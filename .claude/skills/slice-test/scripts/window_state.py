#!/usr/bin/env python3
"""
Window State Detection Module

Provides comprehensive window state detection for UI automation testing.
Detects fullscreen/maximized/minimized states, DPI scaling, and coordinate conversion.

Usage:
    from window_state import WindowStateMonitor, PositionAwareClicker

    # Find window
    hwnd = find_window_by_title("Creality Print")

    # Create monitor
    monitor = WindowStateMonitor(hwnd)
    state = monitor.get_current_state()

    print(f"State: {state.state.value}")
    print(f"DPI: {state.dpi}")
    print(f"Scale: {state.scale_factor}")
"""

import os
import sys
import time
import json
from dataclasses import dataclass, asdict, field
from typing import Optional, Tuple, Dict, Any, Callable, List
from pathlib import Path
from enum import Enum
import ctypes
from ctypes import wintypes


class WindowStateEnum(Enum):
    """Window state enumeration"""
    NORMAL = "normal"
    MINIMIZED = "minimized"
    MAXIMIZED = "maximized"
    FULLSCREEN = "fullscreen"


@dataclass
class WindowInfo:
    """Window information data class"""
    handle: int = 0
    title: str = ""
    class_name: str = ""
    screen_rect: Tuple[int, int, int, int] = (0, 0, 0, 0)  # left, top, right, bottom
    client_rect: Tuple[int, int, int, int] = (0, 0, 0, 0)   # left, top, right, bottom (screen coords)
    client_size: Tuple[int, int] = (0, 0)  # width, height
    state: WindowStateEnum = WindowStateEnum.NORMAL
    dpi: int = 96
    scale_factor: float = 1.0
    is_visible: bool = True
    is_enabled: bool = True
    is_focused: bool = False
    monitor_index: int = 0
    monitor_rect: Tuple[int, int, int, int] = (0, 0, 0, 0)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        d = asdict(self)
        d['state'] = self.state.value
        d['screen_rect'] = list(self.screen_rect)
        d['client_rect'] = list(self.client_rect)
        d['client_size'] = list(self.client_size)
        d['monitor_rect'] = list(self.monitor_rect)
        return d

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'WindowInfo':
        """Create from dictionary"""
        data = data.copy()
        data['state'] = WindowStateEnum(data.get('state', 'normal'))
        data['screen_rect'] = tuple(data.get('screen_rect', (0, 0, 0, 0)))
        data['client_rect'] = tuple(data.get('client_rect', (0, 0, 0, 0)))
        data['client_size'] = tuple(data.get('client_size', (0, 0)))
        data['monitor_rect'] = tuple(data.get('monitor_rect', (0, 0, 0, 0)))
        return cls(**data)

    @property
    def width(self) -> int:
        return self.screen_rect[2] - self.screen_rect[0]

    @property
    def height(self) -> int:
        return self.screen_rect[3] - self.screen_rect[1]

    @property
    def screen_x(self) -> int:
        return self.screen_rect[0]

    @property
    def screen_y(self) -> int:
        return self.screen_rect[1]

    @property
    def client_x(self) -> int:
        return self.client_rect[0]

    @property
    def client_y(self) -> int:
        return self.client_rect[1]

    @property
    def client_width(self) -> int:
        return self.client_size[0]

    @property
    def client_height(self) -> int:
        return self.client_size[1]


class WinAPI:
    """Windows API wrapper class"""

    # Window style constants
    GWL_STYLE = -16
    GWL_EXSTYLE = -20
    WS_CAPTION = 0x00C00000
    WS_THICKFRAME = 0x00040000
    WS_MAXIMIZE = 0x01000000
    WS_MINIMIZE = 0x20000000
    WS_VISIBLE = 0x10000000
    WS_DISABLED = 0x08000000

    # Show window commands
    SW_HIDE = 0
    SW_SHOWNORMAL = 1
    SW_SHOWMINIMIZED = 2
    SW_SHOWMAXIMIZED = 3
    SW_SHOWNOACTIVATE = 4
    SW_SHOW = 5
    SW_MINIMIZE = 6
    SW_SHOWMINNOACTIVE = 7
    SW_SHOWNA = 8
    SW_RESTORE = 9
    SW_SHOWDEFAULT = 10

    # Monitor flags
    MONITOR_DEFAULTTONEAREST = 2

    def __init__(self):
        self._setup_functions()

    def _setup_functions(self):
        """Setup Windows API functions"""
        user32 = ctypes.windll.user32

        # Get window rect
        self._GetWindowRect = user32.GetWindowRect
        self._GetWindowRect.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.RECT)]
        self._GetWindowRect.restype = wintypes.BOOL

        # Get client rect
        self._GetClientRect = user32.GetClientRect
        self._GetClientRect.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.RECT)]
        self._GetClientRect.restype = wintypes.BOOL

        # Coordinate conversion
        self._ScreenToClient = user32.ScreenToClient
        self._ScreenToClient.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.POINT)]
        self._ScreenToClient.restype = wintypes.BOOL

        self._ClientToScreen = user32.ClientToScreen
        self._ClientToScreen.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.POINT)]
        self._ClientToScreen.restype = wintypes.BOOL

        # Window state
        self._IsZoomed = user32.IsZoomed
        self._IsZoomed.argtypes = [wintypes.HWND]
        self._IsZoomed.restype = wintypes.BOOL

        self._IsIconic = user32.IsIconic
        self._IsIconic.argtypes = [wintypes.HWND]
        self._IsIconic.restype = wintypes.BOOL

        self._IsWindowVisible = user32.IsWindowVisible
        self._IsWindowVisible.argtypes = [wintypes.HWND]
        self._IsWindowVisible.restype = wintypes.BOOL

        self._IsWindowEnabled = user32.IsWindowEnabled
        self._IsWindowEnabled.argtypes = [wintypes.HWND]
        self._IsWindowEnabled.restype = wintypes.BOOL

        self._GetForegroundWindow = user32.GetForegroundWindow
        self._GetForegroundWindow.restype = wintypes.HWND

        # Window text
        self._GetWindowTextLength = user32.GetWindowTextLengthW
        self._GetWindowTextLength.argtypes = [wintypes.HWND]
        self._GetWindowTextLength.restype = wintypes.INT

        self._GetWindowText = user32.GetWindowTextW
        self._GetWindowText.argtypes = [wintypes.HWND, wintypes.LPWSTR, wintypes.INT]
        self._GetWindowText.restype = wintypes.INT

        # Class name
        self._GetClassName = user32.GetClassNameW
        self._GetClassName.argtypes = [wintypes.HWND, wintypes.LPWSTR, wintypes.INT]
        self._GetClassName.restype = wintypes.INT

        # Window style
        self._GetWindowLongPtr = user32.GetWindowLongPtrW
        self._GetWindowLongPtr.argtypes = [wintypes.HWND, wintypes.INT]
        self._GetWindowLongPtr.restype = wintypes.LONG

        # DPI
        try:
            self._GetDpiForWindow = user32.GetDpiForWindow
            self._GetDpiForWindow.argtypes = [wintypes.HWND]
            self._GetDpiForWindow.restype = wintypes.UINT
            self._has_dpi_api = True
        except AttributeError:
            self._has_dpi_api = False

        # Monitor functions
        self._MonitorFromWindow = user32.MonitorFromWindow
        self._MonitorFromWindow.argtypes = [wintypes.HWND, wintypes.DWORD]
        self._MonitorFromWindow.restype = wintypes.HMONITOR

        # Setup MONITORINFOEX
        class RECT(ctypes.Structure):
            _fields_ = [
                ("left", wintypes.LONG),
                ("top", wintypes.LONG),
                ("right", wintypes.LONG),
                ("bottom", wintypes.LONG),
            ]

        class MONITORINFOEX(ctypes.Structure):
            _fields_ = [
                ("cbSize", wintypes.DWORD),
                ("rcMonitor", RECT),
                ("rcWork", RECT),
                ("dwFlags", wintypes.DWORD),
                ("szDevice", wintypes.WCHAR * 32),
            ]

        self._MONITORINFOEX = MONITORINFOEX

        self._GetMonitorInfo = user32.GetMonitorInfoW
        self._GetMonitorInfo.argtypes = [wintypes.HMONITOR, ctypes.POINTER(MONITORINFOEX)]
        self._GetMonitorInfo.restype = wintypes.BOOL

        # Show window
        self._ShowWindow = user32.ShowWindow
        self._ShowWindow.argtypes = [wintypes.HWND, wintypes.INT]
        self._ShowWindow.restype = wintypes.BOOL

        # Set foreground window
        self._SetForegroundWindow = user32.SetForegroundWindow
        self._SetForegroundWindow.argtypes = [wintypes.HWND]
        self._SetForegroundWindow.restype = wintypes.BOOL

        # Enum windows
        WNDENUMPROC = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
        self._WNDENUMPROC = WNDENUMPROC
        self._EnumWindows = user32.EnumWindows
        self._EnumWindows.argtypes = [WNDENUMPROC, wintypes.LPARAM]
        self._EnumWindows.restype = wintypes.BOOL


# Global WinAPI instance
_winapi: Optional[WinAPI] = None


def get_winapi() -> Optional[WinAPI]:
    """Get or create WinAPI instance"""
    global _winapi
    if sys.platform != 'win32':
        return None
    if _winapi is None:
        _winapi = WinAPI()
    return _winapi


class WindowStateMonitor:
    """
    Window state monitor

    Monitors window state changes including fullscreen/maximized/minimized states,
    DPI scaling, and position changes.
    """

    def __init__(self, hwnd: int = None):
        self._hwnd = hwnd
        self._current_info: Optional[WindowInfo] = None
        self._callbacks: List[Callable[[WindowInfo, WindowInfo], None]] = []
        self._monitoring = False
        self._poll_interval = 0.1
        self._monitor_thread = None
        self._winapi = get_winapi()

    def set_window(self, hwnd: int):
        """Set window handle to monitor"""
        self._hwnd = hwnd

    def get_current_state(self) -> WindowInfo:
        """Get current window state"""
        if self._winapi:
            return self._get_state_win32()
        return WindowInfo()

    def _get_state_win32(self) -> WindowInfo:
        """Get state using Windows API"""
        info = WindowInfo(handle=self._hwnd)

        if not self._hwnd:
            return info

        try:
            api = self._winapi

            # Window title
            length = api._GetWindowTextLength(self._hwnd)
            if length > 0:
                buffer = ctypes.create_unicode_buffer(length + 1)
                api._GetWindowText(self._hwnd, buffer, length + 1)
                info.title = buffer.value

            # Class name
            buffer = ctypes.create_unicode_buffer(256)
            api._GetClassName(self._hwnd, buffer, 256)
            info.class_name = buffer.value

            # Window rect
            rect = wintypes.RECT()
            api._GetWindowRect(self._hwnd, ctypes.byref(rect))
            info.screen_rect = (rect.left, rect.top, rect.right, rect.bottom)

            # Client rect (relative to window)
            client_rect = wintypes.RECT()
            api._GetClientRect(self._hwnd, ctypes.byref(client_rect))
            info.client_size = (client_rect.right, client_rect.bottom)

            # Convert client origin to screen coordinates
            point = wintypes.POINT(0, 0)
            api._ClientToScreen(self._hwnd, ctypes.byref(point))
            info.client_rect = (
                point.x, point.y,
                point.x + client_rect.right,
                point.y + client_rect.bottom
            )

            # Determine window state
            if api._IsIconic(self._hwnd):
                info.state = WindowStateEnum.MINIMIZED
            elif api._IsZoomed(self._hwnd):
                info.state = WindowStateEnum.MAXIMIZED
            elif self._check_fullscreen():
                info.state = WindowStateEnum.FULLSCREEN
            else:
                info.state = WindowStateEnum.NORMAL

            # DPI
            if api._has_dpi_api:
                info.dpi = api._GetDpiForWindow(self._hwnd)
            else:
                info.dpi = 96
            info.scale_factor = info.dpi / 96.0

            # Visibility and focus
            info.is_visible = bool(api._IsWindowVisible(self._hwnd))
            info.is_enabled = bool(api._IsWindowEnabled(self._hwnd))
            info.is_focused = (api._GetForegroundWindow() == self._hwnd)

            # Monitor info
            monitor = api._MonitorFromWindow(self._hwnd, api.MONITOR_DEFAULTTONEAREST)
            if monitor:
                mi = api._MONITORINFOEX()
                mi.cbSize = ctypes.sizeof(api._MONITORINFOEX)
                if api._GetMonitorInfo(monitor, ctypes.byref(mi)):
                    info.monitor_rect = (
                        mi.rcMonitor.left, mi.rcMonitor.top,
                        mi.rcMonitor.right, mi.rcMonitor.bottom
                    )

        except Exception as e:
            print(f"Error getting window state: {e}")

        self._current_info = info
        return info

    def _check_fullscreen(self) -> bool:
        """Check if window is fullscreen"""
        if not self._hwnd:
            return False

        try:
            api = self._winapi

            # Check window style for borders
            style = api._GetWindowLongPtr(self._hwnd, api.GWL_STYLE)
            has_caption = style & api.WS_CAPTION
            has_thickframe = style & api.WS_THICKFRAME

            if has_caption or has_thickframe:
                return False

            # Compare window and monitor size
            rect = wintypes.RECT()
            api._GetWindowRect(self._hwnd, ctypes.byref(rect))

            monitor = api._MonitorFromWindow(self._hwnd, api.MONITOR_DEFAULTTONEAREST)
            if monitor:
                mi = api._MONITORINFOEX()
                mi.cbSize = ctypes.sizeof(api._MONITORINFOEX)
                if api._GetMonitorInfo(monitor, ctypes.byref(mi)):
                    return (rect.left <= mi.rcMonitor.left and
                            rect.top <= mi.rcMonitor.top and
                            rect.right >= mi.rcMonitor.right and
                            rect.bottom >= mi.rcMonitor.bottom)
        except Exception as e:
            print(f"Error checking fullscreen: {e}")

        return False

    def screen_to_client(self, x: int, y: int) -> Tuple[int, int]:
        """Convert screen coordinates to client coordinates"""
        if not self._hwnd or not self._winapi:
            return x, y

        point = wintypes.POINT(x, y)
        self._winapi._ScreenToClient(self._hwnd, ctypes.byref(point))
        return point.x, point.y

    def client_to_screen(self, x: int, y: int) -> Tuple[int, int]:
        """Convert client coordinates to screen coordinates"""
        if not self._hwnd or not self._winapi:
            return x, y

        point = wintypes.POINT(x, y)
        self._winapi._ClientToScreen(self._hwnd, ctypes.byref(point))
        return point.x, point.y

    def is_fullscreen(self) -> bool:
        """Check if window is fullscreen"""
        return self.get_current_state().state == WindowStateEnum.FULLSCREEN

    def is_maximized(self) -> bool:
        """Check if window is maximized"""
        return self.get_current_state().state == WindowStateEnum.MAXIMIZED

    def is_minimized(self) -> bool:
        """Check if window is minimized"""
        return self.get_current_state().state == WindowStateEnum.MINIMIZED

    def get_dpi(self) -> int:
        """Get window DPI"""
        return self.get_current_state().dpi

    def get_scale_factor(self) -> float:
        """Get DPI scale factor"""
        return self.get_current_state().scale_factor

    def maximize(self) -> bool:
        """Maximize window"""
        if not self._hwnd or not self._winapi:
            return False
        return bool(self._winapi._ShowWindow(self._hwnd, self._winapi.SW_SHOWMAXIMIZED))

    def minimize(self) -> bool:
        """Minimize window"""
        if not self._hwnd or not self._winapi:
            return False
        return bool(self._winapi._ShowWindow(self._hwnd, self._winapi.SW_SHOWMINIMIZED))

    def restore(self) -> bool:
        """Restore window"""
        if not self._hwnd or not self._winapi:
            return False
        return bool(self._winapi._ShowWindow(self._hwnd, self._winapi.SW_RESTORE))

    def bring_to_front(self) -> bool:
        """Bring window to front"""
        if not self._hwnd or not self._winapi:
            return False
        return bool(self._winapi._SetForegroundWindow(self._hwnd))

    def register_callback(self, callback: Callable[[WindowInfo, WindowInfo], None]):
        """
        Register state change callback

        Args:
            callback: Function receiving (old_state, new_state) parameters
        """
        self._callbacks.append(callback)

    def start_monitoring(self, interval: float = 0.1):
        """Start monitoring window state changes"""
        import threading

        self._monitoring = True
        self._poll_interval = interval

        def monitor_loop():
            prev_info = self.get_current_state()

            while self._monitoring:
                time.sleep(self._poll_interval)
                curr_info = self.get_current_state()

                if self._has_state_changed(prev_info, curr_info):
                    for callback in self._callbacks:
                        try:
                            callback(prev_info, curr_info)
                        except Exception as e:
                            print(f"Callback error: {e}")

                prev_info = curr_info

        self._monitor_thread = threading.Thread(target=monitor_loop, daemon=True)
        self._monitor_thread.start()

    def stop_monitoring(self):
        """Stop monitoring"""
        self._monitoring = False

    def _has_state_changed(self, old: WindowInfo, new: WindowInfo) -> bool:
        """Check if state has changed"""
        return (old.state != new.state or
                old.screen_rect != new.screen_rect or
                old.dpi != new.dpi or
                old.is_focused != new.is_focused)

    def export_state(self, filepath: str = None) -> str:
        """Export state to JSON file"""
        info = self.get_current_state()
        json_str = json.dumps(info.to_dict(), indent=2, ensure_ascii=False)

        if filepath:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(json_str)

        return json_str


class PositionAwareClicker:
    """
    Position-aware clicker

    Handles clicks considering window state, DPI scaling, and coordinate conversion.
    """

    def __init__(self, monitor: WindowStateMonitor):
        self.monitor = monitor

        try:
            import pyautogui
            self._pyautogui = pyautogui
            self._has_pyautogui = True
        except ImportError:
            self._has_pyautogui = False
            self._pyautogui = None

    def click_at_screen_pos(self, x: int, y: int,
                            button: str = 'left',
                            clicks: int = 1,
                            adjust_for_state: bool = True) -> bool:
        """
        Click at screen position

        Args:
            x, y: Screen coordinates
            button: Mouse button ('left', 'right', 'middle')
            clicks: Number of clicks
            adjust_for_state: Whether to restore minimized window
        """
        if not self._has_pyautogui:
            print("pyautogui not available")
            return False

        state = self.monitor.get_current_state()

        # Restore if minimized
        if adjust_for_state and state.state == WindowStateEnum.MINIMIZED:
            self.monitor.restore()
            time.sleep(0.3)

        try:
            self._pyautogui.click(x, y, clicks=clicks, button=button)
            return True
        except Exception as e:
            print(f"Click failed: {e}")
            return False

    def click_at_client_pos(self, x: int, y: int,
                            button: str = 'left',
                            clicks: int = 1) -> bool:
        """
        Click at client position (relative to window client area)

        Args:
            x, y: Client area coordinates
            button: Mouse button
            clicks: Number of clicks
        """
        # Convert to screen coordinates
        screen_x, screen_y = self.monitor.client_to_screen(x, y)
        return self.click_at_screen_pos(screen_x, screen_y, button, clicks)

    def click_element_rect(self, rect: Tuple[int, int, int, int],
                           button: str = 'left',
                           clicks: int = 1,
                           offset: Tuple[int, int] = (0, 0)) -> bool:
        """
        Click at center of element rectangle

        Args:
            rect: Element rectangle (left, top, right, bottom) in screen coords
            button: Mouse button
            clicks: Number of clicks
            offset: Offset from center (x, y)
        """
        center_x = (rect[0] + rect[2]) // 2 + offset[0]
        center_y = (rect[1] + rect[3]) // 2 + offset[1]
        return self.click_at_screen_pos(center_x, center_y, button, clicks)

    def double_click_at_screen_pos(self, x: int, y: int) -> bool:
        """Double click at screen position"""
        return self.click_at_screen_pos(x, y, clicks=2)

    def right_click_at_screen_pos(self, x: int, y: int) -> bool:
        """Right click at screen position"""
        return self.click_at_screen_pos(x, y, button='right')

    def drag(self, start_x: int, start_y: int, end_x: int, end_y: int,
             duration: float = 0.5) -> bool:
        """
        Drag from start to end position

        Args:
            start_x, start_y: Start screen coordinates
            end_x, end_y: End screen coordinates
            duration: Drag duration in seconds
        """
        if not self._has_pyautogui:
            return False

        try:
            self._pyautogui.moveTo(start_x, start_y)
            self._pyautogui.drag(end_x - start_x, end_y - start_y,
                                 duration=duration, button='left')
            return True
        except Exception as e:
            print(f"Drag failed: {e}")
            return False

    def scroll(self, x: int, y: int, clicks: int = 1) -> bool:
        """
        Scroll at position

        Args:
            x, y: Screen coordinates
            clicks: Number of scroll clicks (positive=up, negative=down)
        """
        if not self._has_pyautogui:
            return False

        try:
            self._pyautogui.click(x, y)  # Focus the area
            self._pyautogui.scroll(clicks, x, y)
            return True
        except Exception as e:
            print(f"Scroll failed: {e}")
            return False


def find_window_by_title(title_pattern: str) -> Optional[int]:
    """Find window by title (partial match, case insensitive)"""
    if sys.platform != 'win32':
        return None

    api = get_winapi()
    if not api:
        return None

    result = [None]

    def enum_windows_proc(hwnd, lParam):
        length = api._GetWindowTextLength(hwnd)
        if length > 0:
            buffer = ctypes.create_unicode_buffer(length + 1)
            api._GetWindowText(hwnd, buffer, length + 1)
            if title_pattern.lower() in buffer.value.lower():
                result[0] = hwnd
                return False
        return True

    api._EnumWindows(api._WNDENUMPROC(enum_windows_proc), 0)
    return result[0]


def find_all_windows_by_title(title_pattern: str) -> List[int]:
    """Find all windows matching title pattern"""
    if sys.platform != 'win32':
        return []

    api = get_winapi()
    if not api:
        return []

    result = []

    def enum_windows_proc(hwnd, lParam):
        length = api._GetWindowTextLength(hwnd)
        if length > 0:
            buffer = ctypes.create_unicode_buffer(length + 1)
            api._GetWindowText(hwnd, buffer, length + 1)
            if title_pattern.lower() in buffer.value.lower():
                result.append(hwnd)
        return True

    api._EnumWindows(api._WNDENUMPROC(enum_windows_proc), 0)
    return result


def get_focused_window() -> Optional[int]:
    """Get currently focused window handle"""
    api = get_winapi()
    if api:
        return api._GetForegroundWindow()
    return None


# Test / Demo
if __name__ == '__main__':
    print("=" * 60)
    print("Window State Detection Module - Test")
    print("=" * 60)

    # Find Creality Print window
    print("\nSearching for Creality Print window...")
    hwnd = find_window_by_title("Creality Print")

    if hwnd:
        print(f"Found window handle: {hwnd}")

        # Create monitor
        monitor = WindowStateMonitor(hwnd)
        state = monitor.get_current_state()

        print(f"\nWindow Information:")
        print(f"  Title: {state.title}")
        print(f"  Class: {state.class_name}")
        print(f"  State: {state.state.value}")
        print(f"  DPI: {state.dpi}")
        print(f"  Scale Factor: {state.scale_factor:.2f}x")
        print(f"  Visible: {state.is_visible}")
        print(f"  Focused: {state.is_focused}")
        print(f"\n  Screen Position: ({state.screen_x}, {state.screen_y})")
        print(f"  Window Size: {state.width} x {state.height}")
        print(f"  Client Position: ({state.client_x}, {state.client_y})")
        print(f"  Client Size: {state.client_width} x {state.client_height}")

        # Test coordinate conversion
        print(f"\n  Coordinate Conversion Test:")
        client_x, client_y = 100, 100
        screen_x, screen_y = monitor.client_to_screen(client_x, client_y)
        print(f"    Client ({client_x}, {client_y}) -> Screen ({screen_x}, {screen_y})")
        back_x, back_y = monitor.screen_to_client(screen_x, screen_y)
        print(f"    Screen ({screen_x}, {screen_y}) -> Client ({back_x}, {back_y})")

        # Export to JSON
        print(f"\n  Exporting state to JSON...")
        json_output = monitor.export_state()
        print(f"  {json_output[:200]}...")

    else:
        print("Creality Print window not found. Please start the application first.")
        print("\nListing all windows with 'Print' in title:")
        windows = find_all_windows_by_title("Print")
        for whwnd in windows[:5]:
            monitor = WindowStateMonitor(whwnd)
            state = monitor.get_current_state()
            print(f"  - {state.title} (hwnd={whwnd})")
