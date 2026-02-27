#!/usr/bin/env python3
"""
GUI Automation Module for Creality Print Testing (Enhanced Version)

Provides multi-layer automation strategy optimized for wxWidgets applications:
1. pywinauto Win32 backend (primary) - best for wxWidgets custom controls
2. pywinauto UIA backend (fallback)
3. pyautogui visual automation (last resort)
4. Keyboard shortcuts (safety net)
"""

import os
import sys
import time
import subprocess
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Optional, List, Dict, Any, Tuple

# Import window state detection module
try:
    from window_state import (
        WindowStateMonitor,
        WindowInfo,
        WindowStateEnum,
        PositionAwareClicker,
        find_window_by_title,
        get_focused_window
    )
    HAS_WINDOW_STATE = True
except ImportError:
    HAS_WINDOW_STATE = False

# Try to import automation libraries
try:
    from pywinauto import Application, findwindows
    from pywinauto.timings import Timings
    HAS_PYWINAUTO = True
    # Optimize timings for wxWidgets
    Timings.fast()
except ImportError:
    HAS_PYWINAUTO = False

try:
    import pyautogui
    HAS_PYAUTOGUI = True
except ImportError:
    HAS_PYAUTOGUI = False


class AutomationBackend(Enum):
    """Available automation backends"""
    WIN32 = "win32"        # pywinauto Win32 backend - best for wxWidgets
    UIA = "uia"            # pywinauto UIA backend
    PYAUTOGUI = "pyautogui"  # Visual automation


@dataclass
class GUIConfig:
    """GUI automation configuration"""
    app_path: str
    backend: AutomationBackend = AutomationBackend.WIN32
    startup_timeout: int = 30
    operation_timeout: int = 10
    screenshot_dir: str = ".claude/skills/slice-test/screenshots"
    save_screenshots: bool = True
    slow_motion: float = 0.0


@dataclass
class Locator:
    """Enhanced UI element locator for wxWidgets applications"""
    # Primary identifiers
    title: Optional[str] = None          # Window/control title
    class_name: Optional[str] = None     # wxWidgets class name (e.g., "wxWindow", "Button")
    control_id: Optional[int] = None     # Numeric control ID

    # Alternative identifiers
    name: Optional[str] = None           # pywinauto compatible name
    automation_id: Optional[str] = None  # UI Automation ID
    text: Optional[str] = None           # Visible text content

    # Visual fallback
    image: Optional[str] = None          # Image path for visual matching

    # Search parameters
    index: int = 0
    timeout: int = 10

    # wxWidgets specific
    wx_class: Optional[str] = None       # wxWidgets class name pattern


class GUIAutomation:
    """
    Enhanced GUI automation for Creality Print (wxWidgets).

    Multi-layer strategy:
    1. Win32 backend - identifies windows by class name hierarchy
    2. UIA backend - uses UI Automation properties
    3. Visual fallback - pyautogui image/coordinate based
    """

    # wxWidgets class name patterns commonly used in Creality Print
    WX_CLASS_PATTERNS = {
        'main_window': ['wxWindow', 'wxFrame', 'wxDialog'],
        'button': ['Button', 'SideButton', 'wxButton', 'wxWindow'],
        'panel': ['Panel', 'wxPanel', 'wxWindow'],
        'canvas': ['GLCanvas', 'wxGLCanvas', 'wxWindow'],
        'toolbar': ['ToolBar', 'wxToolBar'],
        'menu': ['Menu', 'wxMenu'],
        'edit': ['Edit', 'wxTextCtrl', 'wxComboBox'],
        'list': ['List', 'wxListCtrl', 'wxListView'],
        'tree': ['Tree', 'wxTreeCtrl'],
        'tab': ['Tab', 'wxNotebook', 'wxChoicebook'],
    }

    def __init__(self, config: GUIConfig):
        self.config = config
        self.app: Optional[Application] = None
        self.main_window = None
        self._running = False
        self._window_handle = None

        # Window state monitor
        self._window_state_mgr: Optional[WindowStateMonitor] = None
        self._position_aware_clicker: Optional[PositionAwareClicker] = None

        # Check dependencies
        if not HAS_PYWINAUTO and not HAS_PYAUTOGUI:
            raise ImportError(
                "No automation backend available. "
                "Install: pip install pywinauto pyautogui"
            )

        # Configure pyautogui
        if HAS_PYAUTOGUI:
            pyautogui.FAILSAFE = True
            pyautogui.PAUSE = max(0.1, config.slow_motion)

        # Create directories
        if config.save_screenshots:
            Path(config.screenshot_dir).mkdir(parents=True, exist_ok=True)

        # Initialize window state monitor
        if HAS_WINDOW_STATE:
            self._window_state_mgr = WindowStateMonitor()
            self._position_aware_clicker = PositionAwareClicker(self._window_state_mgr)

    @property
    def has_native(self) -> bool:
        return HAS_PYWINAUTO

    @property
    def has_visual(self) -> bool:
        return HAS_PYAUTOGUI

    def start_application(self) -> bool:
        """Start Creality Print application"""
        if self._running:
            return True

        app_path = Path(self.config.app_path)
        if not app_path.exists():
            raise FileNotFoundError(f"Application not found: {app_path}")

        print(f"Starting: {app_path}")

        if self.has_native:
            try:
                # Use Win32 backend for wxWidgets (better than UIA for custom controls)
                self.app = Application(backend='win32').start(str(app_path))
                time.sleep(3)

                # Find main window using multiple strategies
                self.main_window = self._find_main_window_win32()
                if self.main_window:
                    self._running = True
                    self._window_handle = self.main_window.handle
                    # Update window state monitor
                    if self._window_state_mgr:
                        self._window_state_mgr.set_window(self._window_handle)
                    print(f"App started (Win32 backend, handle={self._window_handle})")
                    return True
            except Exception as e:
                print(f"Win32 backend failed: {e}, trying UIA...")

            try:
                # Fallback to UIA backend
                self.app = Application(backend='uia').start(str(app_path))
                time.sleep(3)
                self.main_window = self._find_main_window_uia()
                if self.main_window:
                    self._running = True
                    print("App started (UIA backend)")
                    return True
            except Exception as e:
                print(f"UIA backend failed: {e}")

        # Visual fallback: just start the process
        if self.has_visual:
            subprocess.Popen([str(app_path)])
            time.sleep(5)
            self._running = True
            print("App started (visual mode)")
            return True

        return False

    def _find_main_window_win32(self):
        """Find main window using Win32 backend"""
        if not self.has_native:
            return None

        # Strategy 1: Find by process ID
        try:
            windows = findwindows.find_elements(
                process=self.app.process,
                backend='win32'
            )
            if windows:
                # Get the largest window (usually main window)
                main = max(windows, key=lambda w: w.rectangle.width() * w.rectangle.height())
                return self.app.window(handle=main.handle)
        except:
            pass

        # Strategy 2: Find by title pattern
        for pattern in ['Creality Print*', '*Creality*', '*Print*']:
            try:
                win = self.app.window(title_re=pattern)
                if win.exists():
                    return win
            except:
                continue

        # Strategy 3: Top window
        try:
            return self.app.top_window()
        except:
            return None

    def _find_main_window_uia(self):
        """Find main window using UIA backend"""
        if not self.has_native:
            return None

        try:
            return self.app.window(title_re='Creality Print*')
        except:
            return self.app.top_window()

    def close_application(self):
        """Close application with multiple fallback strategies"""
        closed = False

        # Strategy 1: Native close
        if self.main_window and self.has_native:
            try:
                self.main_window.close()
                time.sleep(1)
                closed = True
            except:
                pass

        # Strategy 2: Keyboard shortcut
        if not closed and self.has_visual:
            try:
                pyautogui.hotkey('alt', 'F4')
                time.sleep(0.5)
                # Handle save dialog
                pyautogui.press('escape')
                time.sleep(0.5)
                closed = True
            except:
                pass

        # Strategy 3: Kill process
        if self._running:
            try:
                subprocess.run(
                    ['taskkill', '/F', '/IM', 'CrealityPrint.exe'],
                    capture_output=True, timeout=5
                )
            except:
                pass

        self.app = None
        self.main_window = None
        self._running = False
        self._window_handle = None

    def take_screenshot(self, name: str = None) -> Optional[str]:
        """Take screenshot"""
        if not self.has_visual:
            return None

        timestamp = int(time.time())
        filename = f"{name or 'screenshot'}_{timestamp}.png"
        filepath = Path(self.config.screenshot_dir) / filename

        try:
            screenshot = pyautogui.screenshot()
            screenshot.save(str(filepath))
            return str(filepath)
        except Exception as e:
            print(f"Screenshot failed: {e}")
            return None

    # ==========================================
    # Element Finding - Multi-strategy approach
    # ==========================================

    def find_element(self, locator: Locator, parent=None):
        """
        Find element using multiple strategies.

        Priority:
        1. Win32 by class name (best for wxWidgets)
        2. Win32 by title/text
        3. UIA by automation_id
        4. Visual by image
        """
        if not self.has_native:
            return self._find_element_visual(locator)

        search_root = parent or self.main_window
        if not search_root:
            return None

        # Strategy 1: Win32 by class name
        if locator.class_name:
            try:
                element = search_root.child_window(class_name=locator.class_name)
                if element.exists():
                    return element
            except:
                pass

        # Strategy 2: Win32 by title/name
        if locator.title or locator.name:
            title = locator.title or locator.name
            try:
                element = search_root.child_window(title=title)
                if element.exists():
                    return element
            except:
                pass
            try:
                element = search_root.child_window(title_re=f"*{title}*")
                if element.exists():
                    return element
            except:
                pass

        # Strategy 3: Win32 by control ID
        if locator.control_id:
            try:
                element = search_root.child_window(control_id=locator.control_id)
                if element.exists():
                    return element
            except:
                pass

        # Strategy 4: Find by visible text (content)
        if locator.text:
            try:
                element = search_root.child_window(title_re=f"*{locator.text}*")
                if element.exists():
                    return element
            except:
                pass

        # Strategy 5: Find by wxWidgets class pattern
        if locator.wx_class:
            for pattern in self.WX_CLASS_PATTERNS.get(locator.wx_class, []):
                try:
                    element = search_root.child_window(class_name=pattern)
                    if element.exists():
                        return element
                except:
                    continue

        return None

    def _find_element_visual(self, locator: Locator):
        """Find element using visual recognition"""
        if not self.has_visual or not locator.image:
            return None

        try:
            import cv2
            import numpy as np

            # Take screenshot
            screenshot = pyautogui.screenshot()
            screenshot_cv = cv2.cvtColor(np.array(screenshot), cv2.COLOR_RGB2BGR)

            # Load template
            template = cv2.imread(locator.image)
            if template is None:
                return None

            # Match template
            result = cv2.matchTemplate(screenshot_cv, template, cv2.TM_CCOEFF_NORMED)
            min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)

            if max_val > 0.8:  # Confidence threshold
                h, w = template.shape[:2]
                center = (max_loc[0] + w // 2, max_loc[1] + h // 2)
                return center  # Return coordinates

        except Exception as e:
            print(f"Visual find failed: {e}")

        return None

    # ==========================================
    # Click Operations - Multi-layer fallback
    # ==========================================

    def click_element(self, locator: Locator) -> bool:
        """
        Click element with intelligent fallback.

        Strategies:
        1. Native click (Win32/UIA)
        2. Click by coordinates from native element
        3. Visual click by image
        4. Click by keyboard shortcut
        """
        # Strategy 1: Native click
        if self.has_native:
            element = self.find_element(locator)
            if element:
                try:
                    element.click()
                    time.sleep(self.config.slow_motion)
                    return True
                except Exception as e:
                    print(f"Native click failed: {e}")
                    # Try coordinate-based click
                    try:
                        rect = element.rectangle
                        center = (
                            (rect.left + rect.right) // 2,
                            (rect.top + rect.bottom) // 2
                        )
                        if self.has_visual:
                            pyautogui.click(*center)
                            time.sleep(self.config.slow_motion)
                            return True
                    except:
                        pass

        # Strategy 2: Visual click by image
        if self.has_visual and locator.image:
            try:
                location = pyautogui.locateOnScreen(locator.image, confidence=0.8)
                if location:
                    center = pyautogui.center(location)
                    pyautogui.click(center)
                    time.sleep(self.config.slow_motion)
                    return True
            except:
                pass

        return False

    def click_by_text(self, text: str, parent=None) -> bool:
        """Click element by visible text (works well with wxWidgets)"""
        locator = Locator(text=text)
        element = self.find_element(locator, parent)
        if element:
            try:
                element.click()
                time.sleep(self.config.slow_motion)
                return True
            except:
                pass
        return False

    # ==========================================
    # Input Operations
    # ==========================================

    def type_text(self, text: str, locator: Locator = None, parent=None):
        """Type text into element or focused field"""
        if locator and self.has_native:
            element = self.find_element(locator, parent)
            if element:
                try:
                    element.set_text(text)
                    return True
                except:
                    element.click()
                    time.sleep(0.1)

        # Fallback to keyboard input
        if self.has_visual:
            pyautogui.write(text, interval=0.05)
            time.sleep(self.config.slow_motion)
            return True

        return False

    def press_key(self, key: str):
        """Press a single key"""
        if self.has_visual:
            pyautogui.press(key)
            time.sleep(self.config.slow_motion)

    def hotkey(self, *keys):
        """Press keyboard shortcut"""
        if self.has_visual:
            pyautogui.hotkey(*keys)
            time.sleep(self.config.slow_motion)

    # ==========================================
    # Verification Operations
    # ==========================================

    def is_visible(self, locator: Locator) -> bool:
        """Check if element is visible"""
        if self.has_native:
            element = self.find_element(locator)
            if element:
                try:
                    return element.is_visible()
                except:
                    pass

        if self.has_visual and locator.image:
            try:
                location = pyautogui.locateOnScreen(locator.image, confidence=0.8)
                return location is not None
            except:
                pass

        return False

    def is_enabled(self, locator: Locator) -> bool:
        """Check if element is enabled"""
        if self.has_native:
            element = self.find_element(locator)
            if element:
                try:
                    return element.is_enabled()
                except:
                    pass
        return False

    def get_text(self, locator: Locator) -> str:
        """Get text from element"""
        if self.has_native:
            element = self.find_element(locator)
            if element:
                try:
                    return element.window_text()
                except:
                    pass
        return ""

    def wait_for_element(self, locator: Locator, timeout: int = 10) -> bool:
        """Wait for element to appear"""
        start = time.time()
        while time.time() - start < timeout:
            if self.is_visible(locator):
                return True
            time.sleep(0.5)
        return False

    # ==========================================
    # Utility Operations
    # ==========================================

    def get_window_rect(self) -> Optional[Tuple[int, int, int, int]]:
        """Get main window rectangle (left, top, right, bottom)"""
        if self.main_window and self.has_native:
            try:
                rect = self.main_window.rectangle
                return (rect.left, rect.top, rect.right, rect.bottom)
            except:
                pass
        return None

    def bring_to_front(self):
        """Bring main window to front"""
        if self.main_window and self.has_native:
            try:
                self.main_window.set_focus()
            except:
                pass

    # ==========================================
    # Window State Detection Methods (New)
    # ==========================================

    @property
    def window_state(self) -> Optional[WindowInfo]:
        """Get current window state"""
        if self._window_state_mgr:
            if self._window_handle:
                self._window_state_mgr.set_window(self._window_handle)
            return self._window_state_mgr.get_current_state()
        return None

    def get_window_state_dict(self) -> Dict[str, Any]:
        """Get window state as dictionary"""
        state = self.window_state
        if state:
            return state.to_dict()
        return {}

    def is_fullscreen(self) -> bool:
        """Check if window is fullscreen"""
        if self._window_state_mgr:
            return self._window_state_mgr.is_fullscreen()
        return False

    def is_maximized(self) -> bool:
        """Check if window is maximized"""
        if self._window_state_mgr:
            return self._window_state_mgr.is_maximized()
        return False

    def is_minimized(self) -> bool:
        """Check if window is minimized"""
        if self._window_state_mgr:
            return self._window_state_mgr.is_minimized()
        return False

    def get_dpi(self) -> int:
        """Get current window DPI"""
        if self._window_state_mgr:
            return self._window_state_mgr.get_dpi()
        return 96

    def get_scale_factor(self) -> float:
        """Get DPI scale factor"""
        if self._window_state_mgr:
            return self._window_state_mgr.get_scale_factor()
        return 1.0

    def screen_to_client(self, x: int, y: int) -> Tuple[int, int]:
        """Convert screen coordinates to client coordinates"""
        if self._window_state_mgr:
            return self._window_state_mgr.screen_to_client(x, y)
        return x, y

    def client_to_screen(self, x: int, y: int) -> Tuple[int, int]:
        """Convert client coordinates to screen coordinates"""
        if self._window_state_mgr:
            return self._window_state_mgr.client_to_screen(x, y)
        return x, y

    def maximize_window(self) -> bool:
        """Maximize the window"""
        if self._window_state_mgr:
            return self._window_state_mgr.maximize()
        if self.main_window and self.has_native:
            try:
                self.main_window.maximize()
                return True
            except:
                pass
        return False

    def minimize_window(self) -> bool:
        """Minimize the window"""
        if self._window_state_mgr:
            return self._window_state_mgr.minimize()
        if self.main_window and self.has_native:
            try:
                self.main_window.minimize()
                return True
            except:
                pass
        return False

    def restore_window(self) -> bool:
        """Restore the window from minimized/maximized state"""
        if self._window_state_mgr:
            return self._window_state_mgr.restore()
        if self.main_window and self.has_native:
            try:
                self.main_window.restore()
                return True
            except:
                pass
        return False

    def get_element_center(self, locator: Locator) -> Optional[Tuple[int, int]]:
        """
        Get element center position in screen coordinates

        Returns:
            Tuple (x, y) or None if element not found
        """
        element = self.find_element(locator)
        if element:
            try:
                rect = element.rectangle
                return ((rect.left + rect.right) // 2,
                        (rect.top + rect.bottom) // 2)
            except:
                pass
        return None

    def get_element_client_coords(self, locator: Locator) -> Optional[Tuple[int, int]]:
        """
        Get element position relative to client area

        Returns:
            Tuple (x, y) client coordinates or None
        """
        screen_pos = self.get_element_center(locator)
        if screen_pos:
            return self.screen_to_client(*screen_pos)
        return None

    def click_element_adaptive(self, locator: Locator,
                               wait_for_stable: bool = True,
                               timeout: int = 5) -> bool:
        """
        Adaptive click that considers window state and DPI

        Args:
            locator: Element locator
            wait_for_stable: Wait for window state to stabilize
            timeout: Maximum wait time
        """
        # Wait for window state to stabilize
        if wait_for_stable:
            self._wait_for_window_stable(timeout)

        # Check and handle window state
        if self.is_minimized():
            self.restore_window()
            time.sleep(0.5)

        # Find element
        element = self.find_element(locator)
        if not element:
            return False

        try:
            # Get element screen position
            rect = element.rectangle
            center_x = (rect.left + rect.right) // 2
            center_y = (rect.top + rect.bottom) // 2

            # Use position-aware clicker if available
            if self._position_aware_clicker:
                return self._position_aware_clicker.click_element_rect(
                    (rect.left, rect.top, rect.right, rect.bottom)
                )
            elif self.has_visual:
                pyautogui.click(center_x, center_y)
                time.sleep(self.config.slow_motion)
                return True

        except Exception as e:
            print(f"Adaptive click failed: {e}")

        # Fallback to native click
        return self.click_element(locator)

    def _wait_for_window_stable(self, timeout: int = 5) -> bool:
        """Wait for window state to stabilize"""
        if not self._window_state_mgr:
            return True

        start = time.time()
        prev_state = self.window_state

        while time.time() - start < timeout:
            time.sleep(0.1)
            curr_state = self.window_state

            if prev_state and curr_state:
                # Check if position and state are stable
                if (prev_state.screen_rect == curr_state.screen_rect and
                    prev_state.state == curr_state.state):
                    return True

            prev_state = curr_state

        return False

    def verify_element_position(self, locator: Locator,
                                expected_x: int = None,
                                expected_y: int = None,
                                tolerance: int = 10) -> Tuple[bool, str]:
        """
        Verify element position is within expected range

        Args:
            locator: Element locator
            expected_x: Expected X coordinate (client coords, None to skip)
            expected_y: Expected Y coordinate (client coords, None to skip)
            tolerance: Allowed deviation in pixels

        Returns:
            Tuple (success, message)
        """
        actual_pos = self.get_element_client_coords(locator)
        if actual_pos is None:
            return False, "Element not found"

        actual_x, actual_y = actual_pos

        if expected_x is not None:
            if abs(actual_x - expected_x) > tolerance:
                return False, f"X position mismatch: expected {expected_x}, got {actual_x}"

        if expected_y is not None:
            if abs(actual_y - expected_y) > tolerance:
                return False, f"Y position mismatch: expected {expected_y}, got {actual_y}"

        return True, f"Position verified: ({actual_x}, {actual_y})"

    def export_window_state(self, filepath: str = None) -> str:
        """Export window state to JSON"""
        if self._window_state_mgr:
            return self._window_state_mgr.export_state(filepath)
        return "{}"


def create_automation(app_path: str, **kwargs) -> GUIAutomation:
    """
    Factory function to create GUI automation instance.

    Args:
        app_path: Path to CrealityPrint.exe
        **kwargs: Additional configuration options

    Returns:
        GUIAutomation instance
    """
    config = GUIConfig(app_path=app_path, **kwargs)
    return GUIAutomation(config)


if __name__ == '__main__':
    print("Enhanced GUI Automation Module for Creality Print")
    print(f"pywinauto available: {HAS_PYWINAUTO}")
    print(f"pyautogui available: {HAS_PYAUTOGUI}")
    print(f"window_state available: {HAS_WINDOW_STATE}")

    if HAS_WINDOW_STATE:
        print("\n--- Window State Detection Test ---")
        hwnd = find_window_by_title("Creality Print")
        if hwnd:
            print(f"Found Creality Print window: {hwnd}")
            monitor = WindowStateMonitor(hwnd)
            state = monitor.get_current_state()
            print(f"State: {state.state.value}")
            print(f"DPI: {state.dpi} ({state.scale_factor:.2f}x)")
            print(f"Position: ({state.screen_x}, {state.screen_y})")
            print(f"Size: {state.width} x {state.height}")
        else:
            print("Creality Print window not found")
