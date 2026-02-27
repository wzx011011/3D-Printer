#!/usr/bin/env python3
"""
Creality Print Automated Test Runner

Main script for running slicing tests via CLI.
"""

import argparse
import json
import os
import subprocess
import sys
import time
import yaml
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional, Any

# Add scripts directory to path
script_dir = Path(__file__).parent
sys.path.insert(0, str(script_dir))

from gcode_validator import validate_gcode
from report_generator import ReportGenerator, TestResult, TestSuite


@dataclass
class TestCase:
    """Parsed test case from YAML configuration"""
    id: str
    name: str
    description: str = ""
    input: str = ""
    tags: List[str] = field(default_factory=list)
    timeout: int = 300
    enabled: bool = True
    config: Optional[str] = None
    expected: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: Dict) -> 'TestCase':
        return cls(
            id=data.get('id', 'UNKNOWN'),
            name=data.get('name', 'Unnamed Test'),
            description=data.get('description', ''),
            input=data.get('input', ''),
            tags=data.get('tags', []),
            timeout=data.get('timeout', 300),
            enabled=data.get('enabled', True),
            config=data.get('config'),
            expected=data.get('expected', {})
        )


@dataclass
class TestConfig:
    """Overall test configuration"""
    cli_path: str
    test_data_dir: str
    output_dir: str
    default_timeout: int = 300

    @classmethod
    def from_skill_json(cls, skill_path: Path) -> 'TestConfig':
        with open(skill_path / 'skill.json', 'r', encoding='utf-8') as f:
            data = json.load(f)
        return cls(
            cli_path=data.get('cli_path', 'CrealityPrint.exe'),
            test_data_dir=data.get('test_data_dir', 'tests/data'),
            output_dir=data.get('output_dir', '.claude/skills/slice-test/output'),
            default_timeout=data.get('default_timeout', 300)
        )


class TestRunner:
    """Main test execution engine"""

    def __init__(self, config: TestConfig, verbose: bool = False):
        self.config = config
        self.verbose = verbose
        self.results: List[TestResult] = []
        self.output_base = Path(config.output_dir)

        # Ensure output directory exists
        self.output_base.mkdir(parents=True, exist_ok=True)

        # Resolve CLI path
        self.cli_path = self._resolve_cli_path()

    def _resolve_cli_path(self) -> Path:
        """Resolve CLI executable path"""
        cli = Path(self.config.cli_path)
        if not cli.is_absolute():
            # Try relative to project root
            project_root = Path(__file__).parent.parent.parent.parent.parent
            cli = project_root / cli
        return cli

    def _resolve_input_path(self, input_path: str) -> Path:
        """Resolve input file path"""
        p = Path(input_path)
        if p.is_absolute():
            return p

        # Try relative to test data dir
        project_root = Path(__file__).parent.parent.parent.parent.parent
        test_data = project_root / self.config.test_data_dir / input_path
        if test_data.exists():
            return test_data

        # Try as-is relative to project root
        full_path = project_root / input_path
        if full_path.exists():
            return full_path

        return p

    def load_test_cases(self, yaml_path: str) -> List[TestCase]:
        """Load test cases from YAML file"""
        with open(yaml_path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)

        cases = []
        for tc_data in data.get('test_cases', []):
            cases.append(TestCase.from_dict(tc_data))

        return cases

    def filter_by_tags(self, cases: List[TestCase], tags: List[str]) -> List[TestCase]:
        """Filter test cases by tags"""
        if not tags:
            return cases

        filtered = []
        for case in cases:
            if any(tag in case.tags for tag in tags):
                filtered.append(case)

        return filtered

    def run_test(self, case: TestCase) -> TestResult:
        """Execute a single test case"""
        result = TestResult(
            test_id=case.id,
            name=case.name,
            status='passed',
            duration=0,
            input_file=case.input,
            tags=case.tags.copy()
        )

        if self.verbose:
            print(f"\n{'='*60}")
            print(f"Running: {case.id} - {case.name}")
            print(f"Input: {case.input}")
            print(f"{'='*60}")

        # Resolve input path
        input_path = self._resolve_input_path(case.input)

        if not input_path.exists():
            result.status = 'failed'
            result.error_message = f"Input file not found: {input_path}"
            return result

        # Create output directory for this test
        test_output_dir = self.output_base / f"{case.id}_{int(time.time())}"
        test_output_dir.mkdir(parents=True, exist_ok=True)

        # Build CLI command
        # Note: --slice requires parameter: 0=all plates, i=specific plate
        cmd = [
            str(self.cli_path),
            str(input_path),
            '--slice', '0',
            '--outputdir', str(test_output_dir)
        ]

        if case.config:
            config_path = self._resolve_input_path(case.config)
            if config_path.exists():
                cmd.extend(['--load_settings', str(config_path)])

        if self.verbose:
            print(f"Command: {' '.join(cmd)}")

        # Execute CLI
        start_time = time.time()
        try:
            process = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=case.timeout,
                cwd=str(Path(__file__).parent.parent.parent.parent.parent)
            )
            result.return_code = process.returncode
            result.stdout = process.stdout[:5000] if process.stdout else None
            result.stderr = process.stderr[:5000] if process.stderr else None

            if self.verbose:
                if process.stdout:
                    print(f"STDOUT: {process.stdout[:1000]}")
                if process.stderr:
                    print(f"STDERR: {process.stderr[:1000]}")

        except subprocess.TimeoutExpired:
            result.status = 'failed'
            result.error_message = f"Test timed out after {case.timeout} seconds"
            result.duration = case.timeout
            return result
        except FileNotFoundError:
            result.status = 'error'
            result.error_message = f"CLI executable not found: {self.cli_path}"
            return result
        except Exception as e:
            result.status = 'error'
            result.error_message = f"Execution error: {str(e)}"
            return result

        result.duration = time.time() - start_time

        # Check return code - support both single code and list of acceptable codes
        expected_code = case.expected.get('return_code', 0)
        acceptable_codes = case.expected.get('return_code_accept', [expected_code])

        if result.return_code not in acceptable_codes:
            result.status = 'failed'
            result.error_message = f"Unexpected return code: {result.return_code} (expected one of {acceptable_codes})"
            return result

        # For negative tests, we're done here
        if expected_code != 0 and result.return_code == expected_code:
            return result

        # Find generated G-code file
        gcode_files = list(test_output_dir.glob('**/*.gcode'))
        if not gcode_files:
            # Try .gco extension
            gcode_files = list(test_output_dir.glob('**/*.gco'))

        if case.expected.get('gcode_exists', True):
            if not gcode_files:
                result.status = 'failed'
                result.error_message = "No G-code file generated"
                return result

            # Validate G-code
            gcode_path = gcode_files[0]
            result.output_file = str(gcode_path)

            validation = validate_gcode(
                str(gcode_path),
                min_lines=case.expected.get('min_lines', 0),
                max_lines=case.expected.get('max_lines', 1000000),
                required_keywords=case.expected.get('gcode_keywords')
            )

            result.gcode_valid = validation.is_valid

            if validation.stats:
                result.gcode_stats = {
                    'total_lines': validation.stats.total_lines,
                    'command_lines': validation.stats.command_lines,
                    'layers': validation.stats.layers,
                    'extrusion_moves': validation.stats.extrusion_moves,
                }

            if not validation.is_valid:
                result.status = 'failed'
                result.error_message = '; '.join(validation.errors)

        return result

    def run_all(self, cases: List[TestCase]) -> TestSuite:
        """Run all test cases and return results"""
        suite = TestSuite(name="Creality Print Slicing Tests")
        suite.start_time = datetime.now()

        print(f"\nRunning {len(cases)} test(s)...\n")

        for i, case in enumerate(cases, 1):
            if not case.enabled:
                print(f"[{i}/{len(cases)}] SKIP: {case.id}")
                result = TestResult(
                    test_id=case.id,
                    name=case.name,
                    status='skipped',
                    duration=0,
                    input_file=case.input,
                    tags=case.tags,
                    error_message="Test disabled"
                )
            else:
                print(f"[{i}/{len(cases)}] RUN: {case.id} - {case.name}")
                result = self.run_test(case)

            suite.results.append(result)

            # Print result
            status_icons = {
                'passed': '[PASS]',
                'failed': '[FAIL]',
                'skipped': '[SKIP]',
                'error': '[ERR!]'
            }
            icon = status_icons.get(result.status, '[????]')
            duration_str = f" ({result.duration:.2f}s)" if result.duration else ""
            print(f"  {icon} {case.id}{duration_str}")

            if result.error_message:
                print(f"       Error: {result.error_message}")

        suite.end_time = datetime.now()
        return suite


def main():
    parser = argparse.ArgumentParser(
        description='Creality Print Automated Test Runner',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Examples:
  # Run all smoke tests
  python run_tests.py --cli "build/package/CrealityPrint.exe" --tags smoke

  # Run specific test case file
  python run_tests.py --cli "build/package/CrealityPrint.exe" --test-case config/test_cases/basic_slice.yaml

  # Generate HTML report
  python run_tests.py --cli "build/package/CrealityPrint.exe" --tags basic --report html
        '''
    )

    parser.add_argument(
        '--cli', '-c',
        required=True,
        help='Path to CrealityPrint.exe CLI executable'
    )

    parser.add_argument(
        '--test-case', '-t',
        action='append',
        default=[],
        help='Path to test case YAML file (can specify multiple)'
    )

    parser.add_argument(
        '--tags',
        nargs='*',
        default=[],
        help='Filter tests by tags (space-separated)'
    )

    parser.add_argument(
        '--report', '-r',
        choices=['html', 'junit', 'console', 'all'],
        default='console',
        help='Report format to generate'
    )

    parser.add_argument(
        '--output', '-o',
        default=None,
        help='Output directory for reports and test results'
    )

    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Enable verbose output'
    )

    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Show tests that would run without executing'
    )

    args = parser.parse_args()

    # Determine skill directory
    skill_dir = Path(__file__).parent.parent

    # Load default config from skill.json
    config = TestConfig.from_skill_json(skill_dir)
    config.cli_path = args.cli

    if args.output:
        config.output_dir = args.output

    # Create runner
    runner = TestRunner(config, verbose=args.verbose)

    # Determine test case files
    test_case_files = args.test_case
    if not test_case_files:
        # Use default test case files
        default_cases = skill_dir / 'config' / 'test_cases'
        if default_cases.exists():
            test_case_files = list(default_cases.glob('*.yaml'))

    if not test_case_files:
        print("Error: No test case files found")
        print("Specify --test-case or ensure config/test_cases/*.yaml exists")
        sys.exit(1)

    # Load all test cases
    all_cases = []
    for tc_file in test_case_files:
        if isinstance(tc_file, str):
            tc_file = Path(tc_file)
        if tc_file.exists():
            cases = runner.load_test_cases(str(tc_file))
            all_cases.extend(cases)
            if args.verbose:
                print(f"Loaded {len(cases)} test(s) from {tc_file}")

    # Filter by tags
    if args.tags:
        all_cases = runner.filter_by_tags(all_cases, args.tags)
        if not all_cases:
            print(f"No tests match tags: {args.tags}")
            sys.exit(0)

    if args.dry_run:
        print(f"\nDry run - {len(all_cases)} test(s) would be executed:")
        for case in all_cases:
            tags_str = ', '.join(case.tags) if case.tags else 'none'
            print(f"  - {case.id}: {case.name} [tags: {tags_str}]")
        sys.exit(0)

    # Run tests
    suite = runner.run_all(all_cases)

    # Generate reports
    report_gen = ReportGenerator(config.output_dir)

    if args.report in ['html', 'all']:
        html_path = report_gen.generate_html(suite)
        print(f"\nHTML report: {html_path}")

    if args.report in ['junit', 'all']:
        junit_path = report_gen.generate_junit(suite)
        print(f"JUnit report: {junit_path}")

    print(report_gen.generate_console(suite))

    # Exit with appropriate code
    if suite.failed > 0:
        sys.exit(1)
    sys.exit(0)


if __name__ == '__main__':
    main()
