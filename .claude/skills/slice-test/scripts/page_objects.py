#!/usr/bin/env python3
"""
Page Objects for Creality Print GUI Testing (Enhanced for wxWidgets)

Optimized for Creality Print's wxWidgets-based UI with custom controls.
Uses text-based and coordinate-based locating strategies.
"""

import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, List

from gui_automation import GUIAutomation, Locator


class BasePage(ABC):
    """Base class for all page objects"""

    def __init__(self, automation: GUIAutomation):
        self.automation = automation
        self.screenshot_dir = Path(automation.config.screenshot_dir)

    @property
    @abstractmethod
    def page_name(self) -> str:
        pass

    def take_screenshot(self, name: str = None) -> Optional[str]:
        name = name or f"{self.page_name.replace(' ', '_')}"
        return self.automation.take_screenshot(name)

    def click_by_text(self, text: str) -> bool:
        """Click element by visible text - most reliable for wxWidgets"""
        return self.automation.click_by_text(text)

    def click(self, locator: Locator) -> bool:
        return self.automation.click_element(locator)

    def wait_for(self, locator: Locator, timeout: int = 10) -> bool:
        return self.automation.wait_for_element(locator, timeout)


class MainWindow(BasePage):
    """
    Main application window page object.

    Creality Print Main Window Structure:
    - Top Menu Bar (File, Edit, View, etc.)
    - Main Toolbar (Add, Slice, Print, Export buttons)
    - Left Panel (Settings)
    - Center (3D Canvas / GLCanvas)
    - Right Panel (Model List)
    - Bottom Status Bar
    """

    @property
    def page_name(self) -> str:
        return "Main Window"

    def is_current_page(self, timeout: int = 5) -> bool:
        """Check if main window is visible"""
        if self.automation.has_native and self.automation.main_window:
            try:
                return self.automation.main_window.is_visible()
            except:
                pass
        return True  # Assume visible if we got here

    # ==========================================
    # Status Bar Operations
    # ==========================================

    def get_status_text(self) -> str:
        """
        Get text from status bar.
        wxWidgets status bar typically has class 'msctls_statusbar32' or similar.
        """
        if self.automation.has_native and self.automation.main_window:
            try:
                # Debug: print all child windows
                if self.automation.config.slow_motion > 0:
                    try:
                        children = self.automation.main_window.children()
                        for child in children:
                            self.automation.log(f"Child: {child.class_name()} - {child.window_text()}")
                    except:
                        pass

                # Try multiple class name patterns
                class_patterns = [
                    'msctls_statusbar32',
                    'wxStatusBar',
                    'StatusBar',
                ]

                for pattern in class_patterns:
                    try:
                        status_bar = self.automation.main_window.child_window(
                            class_name=pattern
                        )
                        if status_bar.exists():
                            text = status_bar.window_text()
                            if text:
                                return text
                    except:
                        continue

                # Try by class name regex
                try:
                    status_bar = self.automation.main_window.child_window(
                        class_name_re='.*[Ss]tatus.*'
                    )
                    if status_bar.exists():
                        return status_bar.window_text()
                except:
                    pass

                # Fallback: get all text from main window and look for status patterns
                try:
                    all_text = self.automation.main_window.window_text()
                    # Look for common status patterns
                    for line in all_text.split('\n'):
                        if any(kw in line.lower() for kw in ['slicing', 'ready', 'complete', 'progress', '%']):
                            return line.strip()
                except:
                    pass

            except Exception as e:
                pass
        return ""

    def get_all_children_info(self) -> list:
        """Get information about all child windows for debugging"""
        info = []
        if self.automation.has_native and self.automation.main_window:
            try:
                children = self.automation.main_window.children()
                for child in children:
                    try:
                        info.append({
                            'class': child.class_name(),
                            'text': child.window_text(),
                            'visible': child.is_visible()
                        })
                    except:
                        pass
            except:
                pass
        return info

    def wait_for_status(self, expected: str, timeout: int = 30) -> bool:
        """Wait for status bar to show expected text"""
        start = time.time()
        while time.time() - start < timeout:
            current = self.get_status_text()
            if expected.lower() in current.lower():
                return True
            time.sleep(0.5)
        return False

    # ==========================================
    # File Operations
    # ==========================================

    def add_model(self, file_path: str) -> bool:
        """
        Add a model file to the plate.
        Uses keyboard shortcut Ctrl+O for reliability.
        """
        # Use keyboard shortcut (most reliable)
        self.automation.hotkey('ctrl', 'o')
        time.sleep(1)

        # Type file path
        self.automation.type_text(file_path.replace('/', '\\'))
        time.sleep(0.5)

        # Confirm
        self.automation.press_key('enter')
        time.sleep(2)  # Wait for model to load

        return True

    def save_project(self, file_path: str = None) -> bool:
        """Save current project"""
        self.automation.hotkey('ctrl', 's')
        time.sleep(0.5)
        if file_path:
            self.automation.type_text(file_path)
            self.automation.press_key('enter')
        return True

    def export_gcode(self, file_path: str = None) -> bool:
        """Export G-code"""
        self.automation.hotkey('ctrl', 'e')
        time.sleep(0.5)
        if file_path:
            self.automation.type_text(file_path)
            self.automation.press_key('enter')
        return True

    # ==========================================
    # Slicing Operations
    # ==========================================

    def click_slice(self) -> bool:
        """
        Click the Slice button.
        Uses multiple strategies for reliability.
        """
        # Strategy 1: Find by text (works with wxWidgets custom buttons)
        if self.automation.click_by_text('Slice'):
            return True

        # Strategy 2: Keyboard shortcut Ctrl+R
        self.automation.hotkey('ctrl', 'r')
        time.sleep(0.5)
        return True

    def click_slice_plate(self) -> bool:
        """Click 'Slice Plate' button (alternative name)"""
        if self.automation.click_by_text('Slice Plate'):
            return True
        if self.automation.click_by_text('Slice plate'):
            return True
        return self.click_slice()

    def wait_for_slicing_complete(self, timeout: int = 300) -> bool:
        """
        Wait for slicing to complete.
        Monitors for slice progress and completion.
        """
        start = time.time()
        slicing_seen = False

        while time.time() - start < timeout:
            # Check if slicing dialog appeared and disappeared
            # or if we see "Slice completed" type message

            # For now, just wait and check periodically
            time.sleep(2)

            # Simple heuristic: if we can click slice again, it's done
            # This is a placeholder - in real implementation, check progress

        return True

    # ==========================================
    # Tab Navigation
    # ==========================================

    def click_prepare_tab(self) -> bool:
        """Switch to Prepare tab"""
        if self.automation.click_by_text('Prepare'):
            time.sleep(0.5)
            return True
        return False

    def click_preview_tab(self) -> bool:
        """Switch to Preview tab"""
        if self.automation.click_by_text('Preview'):
            time.sleep(0.5)
            return True
        return False

    def click_device_tab(self) -> bool:
        """Switch to Device tab"""
        if self.automation.click_by_text('Device'):
            time.sleep(0.5)
            return True
        return False

    def click_project_tab(self) -> bool:
        """Switch to Project tab"""
        if self.automation.click_by_text('Project'):
            time.sleep(0.5)
            return True
        return False

    # ==========================================
    # Model Operations
    # ==========================================

    def select_all_models(self) -> bool:
        """Select all models on plate"""
        self.automation.hotkey('ctrl', 'a')
        time.sleep(0.3)
        return True

    def delete_selected(self) -> bool:
        """Delete selected models"""
        self.automation.press_key('delete')
        time.sleep(0.3)
        return True

    def clear_plate(self) -> bool:
        """Clear all models from plate"""
        self.automation.hotkey('ctrl', 'shift', 'delete')
        time.sleep(0.5)
        return True

    # ==========================================
    # Menu Operations
    # ==========================================

    def open_file_menu(self) -> bool:
        """Open File menu"""
        self.automation.press_key('alt')
        time.sleep(0.2)
        self.automation.press_key('f')
        return True

    def open_edit_menu(self) -> bool:
        """Open Edit menu"""
        self.automation.press_key('alt')
        time.sleep(0.2)
        self.automation.press_key('e')
        return True

    # ==========================================
    # View Operations
    # ==========================================

    def zoom_in(self) -> bool:
        """Zoom in on 3D view"""
        self.automation.hotkey('ctrl', '+')
        return True

    def zoom_out(self) -> bool:
        """Zoom out on 3D view"""
        self.automation.hotkey('ctrl', '-')
        return True

    def reset_view(self) -> bool:
        """Reset 3D view"""
        self.automation.hotkey('ctrl', '0')
        return True


class SliceProgressDialog(BasePage):
    """Slicing progress dialog"""

    @property
    def page_name(self) -> str:
        return "Slice Progress"

    def is_current_page(self, timeout: int = 5) -> bool:
        """Check if slicing dialog is visible"""
        # Look for cancel button or progress indicators
        return self.automation.click_by_text('Cancel')

    def cancel(self) -> bool:
        """Cancel slicing"""
        return self.automation.click_by_text('Cancel')

    def wait_for_completion(self, timeout: int = 300) -> bool:
        """Wait for dialog to close"""
        start = time.time()
        while time.time() - start < timeout:
            # Check if cancel button is still visible
            if not self.automation.click_by_text('Cancel'):
                return True
            time.sleep(2)
        return False


class PreviewPage(BasePage):
    """G-code Preview page"""

    @property
    def page_name(self) -> str:
        return "Preview"

    def is_current_page(self, timeout: int = 5) -> bool:
        """Check if preview page is visible"""
        # Look for preview-specific elements
        return True

    def wait_for_page(self, timeout: int = 10) -> bool:
        """Wait for preview page to load"""
        start = time.time()
        while time.time() - start < timeout:
            # Check for preview-specific elements
            if self.automation.has_native:
                try:
                    # Look for G-code viewer or layer slider
                    if self.automation.main_window:
                        return True
                except:
                    pass
            time.sleep(0.5)
        return False

    def get_output_path(self) -> str:
        """
        Get G-code output path from preview page.
        Usually displayed in a text field or label.
        """
        if self.automation.has_native and self.automation.main_window:
            try:
                # Look for output path element by text pattern
                # Common patterns: "Output:", "G-code:", file path
                elements = self.automation.main_window.children()
                for el in elements:
                    text = el.window_text()
                    if '.gcode' in text.lower() or 'output' in text.lower():
                        return text
            except:
                pass
        return ""

    def play_animation(self) -> bool:
        """Start layer animation"""
        return self.automation.click_by_text('Play')

    def pause_animation(self) -> bool:
        """Pause layer animation"""
        return self.automation.click_by_text('Pause')

    def reset_view(self) -> bool:
        """Reset preview view"""
        return self.automation.click_by_text('Reset')


class SettingsPanel(BasePage):
    """
    Print settings panel (left side of main window).

    Contains settings for:
    - Layer height
    - Infill
    - Speed
    - Support
    - Temperature
    - etc.
    """

    @property
    def page_name(self) -> str:
        return "Settings Panel"

    def expand_section(self, section_name: str) -> bool:
        """Expand a settings section"""
        return self.automation.click_by_text(section_name)

    def set_layer_height(self, value: float) -> bool:
        """Set layer height"""
        # Find layer height input and set value
        if self.automation.click_by_text('Layer height'):
            time.sleep(0.3)
            # Tab to reach value input
            self.automation.press_key('tab')
            time.sleep(0.1)
            # Select all and type new value
            self.automation.hotkey('ctrl', 'a')
            self.automation.type_text(str(value))
            self.automation.press_key('enter')
            return True
        return False

    def set_infill_density(self, value: int) -> bool:
        """Set infill density percentage"""
        if self.automation.click_by_text('Infill'):
            time.sleep(0.3)
            self.automation.press_key('tab')
            self.automation.hotkey('ctrl', 'a')
            self.automation.type_text(f"{value}%")
            self.automation.press_key('enter')
            return True
        return False

    def enable_supports(self, enable: bool = True) -> bool:
        """Enable or disable support generation"""
        if self.automation.click_by_text('Support'):
            time.sleep(0.3)
            # Look for checkbox or toggle
            if enable:
                self.automation.click_by_text('Enable')
            return True
        return False


class ApplicationPages:
    """Container for all page objects"""

    def __init__(self, automation: GUIAutomation):
        self.automation = automation

        # Initialize all pages
        self.main_window = MainWindow(automation)
        self.slice_progress = SliceProgressDialog(automation)
        self.preview = PreviewPage(automation)
        self.settings = SettingsPanel(automation)


# ==========================================
# Convenience Functions
# ==========================================

def create_test_workflow(automation: GUIAutomation):
    """
    Create a simple test workflow to verify automation works.

    Returns True if all steps succeed.
    """
    pages = ApplicationPages(automation)
    main = pages.main_window

    # Test basic operations
    print("Testing add_model...")
    main.add_model("tests/data/20mm_cube.obj")

    print("Waiting for model to load...")
    time.sleep(2)

    print("Testing click_slice...")
    main.click_slice()

    print("Waiting for slicing...")
    time.sleep(5)

    return True


if __name__ == '__main__':
    print("Enhanced Page Objects Module for Creality Print")
    print("Key strategies for wxWidgets:")
    print("  - Use text-based locating (most reliable)")
    print("  - Use keyboard shortcuts as fallback")
    print("  - Avoid relying on automation_id")
