#!/usr/bin/env python3
"""
G-code Validator Module for Creality Print Testing

Validates generated G-code files for structural integrity and content.
"""

import os
import re
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Tuple
from pathlib import Path


@dataclass
class GCodeStats:
    """Statistics extracted from G-code file"""
    total_lines: int = 0
    comment_lines: int = 0
    command_lines: int = 0
    layers: int = 0
    travel_moves: int = 0
    extrusion_moves: int = 0
    total_extrusion_mm: float = 0.0
    commands_found: Dict[str, int] = field(default_factory=dict)
    keywords_found: List[str] = field(default_factory=list)


@dataclass
class ValidationResult:
    """Result of G-code validation"""
    is_valid: bool
    file_exists: bool
    stats: Optional[GCodeStats] = None
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    missing_keywords: List[str] = field(default_factory=list)


class GCodeValidator:
    """Validates G-code files for correctness and completeness"""

    # Essential G-code commands that should be present
    ESSENTIAL_COMMANDS = {
        'G28': 'Home all axes',
        'G1': 'Linear movement',
    }

    # Common temperature commands
    TEMP_COMMANDS = ['M104', 'M109', 'M140', 'M190']

    # Regex patterns for parsing
    LAYER_PATTERN = re.compile(r';\s*(?:layer|LAYER)\s*:?\s*(\d+)', re.IGNORECASE)
    COMMAND_PATTERN = re.compile(r'^([GM]\d+)')
    EXTRUSION_PATTERN = re.compile(r'E([-\d.]+)')
    # Fixed: use simpler pattern without variable-width lookbehind
    TRAVEL_PATTERN = re.compile(r'G[01]\s+.*F\d+')

    def __init__(self, gcode_path: str):
        self.gcode_path = Path(gcode_path)
        self.lines: List[str] = []
        self.stats = GCodeStats()

    def validate(self,
                 min_lines: int = 0,
                 max_lines: int = 1000000,
                 required_keywords: Optional[List[str]] = None) -> ValidationResult:
        """
        Validate the G-code file against specified criteria.

        Args:
            min_lines: Minimum number of lines expected
            max_lines: Maximum number of lines expected
            required_keywords: List of keywords that must be present

        Returns:
            ValidationResult with validation status and statistics
        """
        result = ValidationResult(is_valid=True, file_exists=False)

        # Check file existence
        if not self.gcode_path.exists():
            result.file_exists = False
            result.is_valid = False
            result.errors.append(f"G-code file not found: {self.gcode_path}")
            return result

        result.file_exists = True

        # Read and parse file
        try:
            self._read_file()
            self._parse_stats()
        except Exception as e:
            result.is_valid = False
            result.errors.append(f"Error parsing G-code: {str(e)}")
            return result

        result.stats = self.stats

        # Validate line count
        if self.stats.total_lines < min_lines:
            result.is_valid = False
            result.errors.append(
                f"Line count {self.stats.total_lines} below minimum {min_lines}"
            )

        if self.stats.total_lines > max_lines:
            result.warnings.append(
                f"Line count {self.stats.total_lines} exceeds maximum {max_lines}"
            )

        # Check required keywords
        if required_keywords:
            result.missing_keywords = self._check_keywords(required_keywords)
            if result.missing_keywords:
                result.is_valid = False
                result.errors.append(
                    f"Missing required keywords: {result.missing_keywords}"
                )

        # Validate essential commands
        missing_essential = self._check_essential_commands()
        if missing_essential:
            result.warnings.append(
                f"Missing essential commands: {missing_essential}"
            )

        return result

    def _read_file(self):
        """Read G-code file into memory"""
        with open(self.gcode_path, 'r', encoding='utf-8', errors='ignore') as f:
            self.lines = f.readlines()
        self.stats.total_lines = len(self.lines)

    def _parse_stats(self):
        """Parse G-code and extract statistics"""
        current_layer = 0
        last_e = 0.0

        for line in self.lines:
            line = line.strip()

            # Count comments
            if line.startswith(';'):
                self.stats.comment_lines += 1

                # Check for layer markers
                layer_match = self.LAYER_PATTERN.search(line)
                if layer_match:
                    current_layer = int(layer_match.group(1))
                    if current_layer > self.stats.layers:
                        self.stats.layers = current_layer
                continue

            if not line:
                continue

            self.stats.command_lines += 1

            # Extract command
            cmd_match = self.COMMAND_PATTERN.match(line)
            if cmd_match:
                cmd = cmd_match.group(1)
                self.stats.commands_found[cmd] = \
                    self.stats.commands_found.get(cmd, 0) + 1

                # Track movements
                if cmd == 'G0' or cmd == 'G1':
                    # Check for extrusion
                    e_match = self.EXTRUSION_PATTERN.search(line)
                    if e_match:
                        e_val = float(e_match.group(1))
                        if e_val > last_e:
                            self.stats.extrusion_moves += 1
                            self.stats.total_extrusion_mm += e_val - last_e
                        last_e = e_val
                    else:
                        self.stats.travel_moves += 1

    def _check_keywords(self, keywords: List[str]) -> List[str]:
        """Check if all required keywords are present in G-code"""
        missing = []
        content = '\n'.join(self.lines)

        for keyword in keywords:
            # Case-insensitive search for comments, case-sensitive for commands
            if keyword.startswith(';'):
                if keyword.lower() not in content.lower():
                    missing.append(keyword)
            elif not re.search(re.escape(keyword), content, re.IGNORECASE if keyword.startswith(';') else 0):
                # For G/M codes, check if they appear
                if not re.search(rf'\b{re.escape(keyword)}\b', content):
                    missing.append(keyword)

        return missing

    def _check_essential_commands(self) -> List[str]:
        """Check for essential G-code commands"""
        missing = []
        for cmd, desc in self.ESSENTIAL_COMMANDS.items():
            if cmd not in self.stats.commands_found:
                missing.append(f"{cmd} ({desc})")
        return missing

    def get_summary(self) -> str:
        """Get a summary string of the G-code statistics"""
        if not self.stats.total_lines:
            return "No G-code parsed"

        return (
            f"Lines: {self.stats.total_lines} "
            f"(commands: {self.stats.command_lines}, comments: {self.stats.comment_lines}) | "
            f"Layers: {self.stats.layers} | "
            f"Moves: {self.stats.extrusion_moves} extrusion, {self.stats.travel_moves} travel | "
            f"Extrusion: {self.stats.total_extrusion_mm:.2f}mm"
        )


def validate_gcode(gcode_path: str,
                   min_lines: int = 0,
                   max_lines: int = 1000000,
                   required_keywords: Optional[List[str]] = None) -> ValidationResult:
    """
    Convenience function to validate a G-code file.

    Args:
        gcode_path: Path to G-code file
        min_lines: Minimum expected lines
        max_lines: Maximum expected lines
        required_keywords: Keywords that must be present

    Returns:
        ValidationResult object
    """
    validator = GCodeValidator(gcode_path)
    return validator.validate(min_lines, max_lines, required_keywords)


if __name__ == '__main__':
    import sys

    if len(sys.argv) < 2:
        print("Usage: python gcode_validator.py <gcode_file> [keyword1] [keyword2] ...")
        sys.exit(1)

    gcode_file = sys.argv[1]
    keywords = sys.argv[2:] if len(sys.argv) > 2 else None

    result = validate_gcode(gcode_file, required_keywords=keywords)

    print(f"\nValidation Result: {'PASS' if result.is_valid else 'FAIL'}")
    print(f"File exists: {result.file_exists}")

    if result.stats:
        print(f"\nStatistics:")
        print(f"  Total lines: {result.stats.total_lines}")
        print(f"  Command lines: {result.stats.command_lines}")
        print(f"  Layers: {result.stats.layers}")
        print(f"  Extrusion moves: {result.stats.extrusion_moves}")
        print(f"  Travel moves: {result.stats.travel_moves}")

    if result.errors:
        print(f"\nErrors:")
        for e in result.errors:
            print(f"  - {e}")

    if result.warnings:
        print(f"\nWarnings:")
        for w in result.warnings:
            print(f"  - {w}")

    sys.exit(0 if result.is_valid else 1)
