"""
UI Component Reader Module

This module reads UI component positions from the JSON file exported by AutomationMgr.
The positions are relative to the main window's client area.
"""

import json
import os
from dataclasses import dataclass
from typing import Dict, Optional


@dataclass
class UIComponent:
    """Represents a UI component with its position and size."""
    id: str
    type: str
    x: int
    y: int
    width: int
    height: int

    @property
    def center(self) -> tuple:
        """Returns the center point of the component (relative to main window client area)."""
        return (self.x + self.width // 2, self.y + self.height // 2)

    @property
    def rect(self) -> tuple:
        """Returns the component as a rectangle tuple (x, y, width, height)."""
        return (self.x, self.y, self.width, self.height)

    def contains_point(self, px: int, py: int) -> bool:
        """Check if a point is inside this component."""
        return (self.x <= px <= self.x + self.width and
                self.y <= py <= self.y + self.height)


def load_ui_components(data_dir: str) -> Dict[str, UIComponent]:
    """
    Load UI components from the JSON file exported by AutomationMgr.

    Args:
        data_dir: Path to the data directory (e.g., %APPDATA%/CrealityPrint)

    Returns:
        Dictionary mapping component IDs to UIComponent objects.
        Returns empty dict if file doesn't exist or is invalid.
    """
    path = os.path.join(data_dir, "automation", "ui_components.json")

    if not os.path.exists(path):
        return {}

    try:
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        components = {}
        for c in data.get('components', []):
            comp = UIComponent(
                id=c['id'],
                type=c['type'],
                x=c['x'],
                y=c['y'],
                width=c['width'],
                height=c['height']
            )
            components[comp.id] = comp

        return components

    except (json.JSONDecodeError, KeyError, IOError) as e:
        print(f"Error loading UI components: {e}")
        return {}


def get_component(data_dir: str, component_id: str) -> Optional[UIComponent]:
    """
    Get a specific UI component by ID.

    Args:
        data_dir: Path to the data directory
        component_id: The ID of the component to retrieve

    Returns:
        UIComponent if found, None otherwise
    """
    components = load_ui_components(data_dir)
    return components.get(component_id)


def get_timestamp(data_dir: str) -> Optional[int]:
    """
    Get the timestamp of when the UI components were last exported.

    Args:
        data_dir: Path to the data directory

    Returns:
        Unix timestamp as integer, or None if file doesn't exist
    """
    path = os.path.join(data_dir, "automation", "ui_components.json")

    if not os.path.exists(path):
        return None

    try:
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return data.get('timestamp')
    except (json.JSONDecodeError, KeyError, IOError):
        return None


# Common component IDs
COMPONENT_IDS = {
    'SLICE_BUTTON': 'slice_button',
    'SEND_BUTTON': 'send_button',
    'PRINTER_COMBO': 'printer_combo',
    'WIFI_BUTTON': 'wifi_button',
    'MAPPING_BUTTON': 'mapping_button',
}


if __name__ == '__main__':
    # Test the module
    import sys

    if len(sys.argv) > 1:
        data_dir = sys.argv[1]
    else:
        # Default Windows path
        data_dir = os.path.expandvars(r'%APPDATA%\CrealityPrint')

    print(f"Loading UI components from: {data_dir}")

    components = load_ui_components(data_dir)
    timestamp = get_timestamp(data_dir)

    print(f"Timestamp: {timestamp}")
    print(f"Found {len(components)} components:")

    for id, comp in components.items():
        print(f"  {id}: ({comp.x}, {comp.y}) {comp.width}x{comp.height} center={comp.center}")
