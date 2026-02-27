#include "WindowStateManager.hpp"
#include <nlohmann/json.hpp>
#include <fstream>
#include <filesystem>
#include <iostream>

#ifdef _WIN32
#include <ShellScalingApi.h>
#pragma comment(lib, "Shcore.lib")
#endif

namespace Slic3r {

WindowStateManager& WindowStateManager::get_instance() {
    static WindowStateManager instance;
    return instance;
}

#ifdef _WIN32

void WindowStateManager::initialize(void* hwnd) {
    try {
        std::lock_guard<std::recursive_mutex> lock(m_mutex);

        if (hwnd == nullptr) {
            std::cerr << "WindowStateManager::initialize: hwnd is null" << std::endl;
            m_initialized = false;
            return;
        }

        m_hwnd = static_cast<HWND>(hwnd);

        // Verify the window handle is valid
        if (!IsWindow(m_hwnd)) {
            std::cerr << "WindowStateManager::initialize: Invalid window handle" << std::endl;
            m_hwnd = nullptr;
            m_initialized = false;
            return;
        }

        m_initialized = true;
        update_state();

        std::cout << "WindowStateManager initialized successfully" << std::endl;
    }
    catch (const std::exception& e) {
        std::cerr << "WindowStateManager::initialize exception: " << e.what() << std::endl;
        m_initialized = false;
    }
    catch (...) {
        std::cerr << "WindowStateManager::initialize: Unknown exception" << std::endl;
        m_initialized = false;
    }
}

WindowPositionInfo WindowStateManager::get_window_position() {
    if (!m_initialized) {
        return WindowPositionInfo();
    }
    update_state();
    return m_current_state;
}

WindowState WindowStateManager::get_window_state() {
    if (!m_initialized) return WindowState::Normal;
    return get_window_state_win32();
}

bool WindowStateManager::is_fullscreen() {
    if (!m_initialized) return false;
    return check_fullscreen_win32();
}

bool WindowStateManager::is_maximized() {
    if (!m_initialized || !m_hwnd) return false;

    try {
        return IsZoomed(m_hwnd) != FALSE;
    }
    catch (...) {
        return false;
    }
}

bool WindowStateManager::is_minimized() {
    if (!m_initialized || !m_hwnd) return false;

    try {
        return IsIconic(m_hwnd) != FALSE;
    }
    catch (...) {
        return false;
    }
}

bool WindowStateManager::is_normal() {
    return get_window_state() == WindowState::Normal;
}

int WindowStateManager::get_dpi() {
    if (!m_initialized) return 96;
    return get_dpi_win32();
}

float WindowStateManager::get_scale_factor() {
    int dpi = get_dpi();
    return static_cast<float>(dpi) / 96.0f;
}

void WindowStateManager::screen_to_client(int& x, int& y) {
    if (!m_initialized || !m_hwnd) return;

    try {
        POINT pt = {x, y};
        ScreenToClient(m_hwnd, &pt);
        x = pt.x;
        y = pt.y;
    }
    catch (...) {
        // Keep original values on error
    }
}

void WindowStateManager::client_to_screen(int& x, int& y) {
    if (!m_initialized || !m_hwnd) return;

    try {
        POINT pt = {x, y};
        ClientToScreen(m_hwnd, &pt);
        x = pt.x;
        y = pt.y;
    }
    catch (...) {
        // Keep original values on error
    }
}

bool WindowStateManager::check_fullscreen_win32() {
    if (!m_initialized || !m_hwnd) return false;

    try {
        // Check window style for borders
        LONG style = GetWindowLong(m_hwnd, GWL_STYLE);
        if (style == 0) return false;

        bool has_caption = (style & WS_CAPTION) != 0;
        bool has_thickframe = (style & WS_THICKFRAME) != 0;

        if (has_caption || has_thickframe) {
            return false;
        }

        // Compare window size with monitor size
        RECT windowRect;
        if (!GetWindowRect(m_hwnd, &windowRect)) return false;

        HMONITOR monitor = MonitorFromWindow(m_hwnd, MONITOR_DEFAULTTONEAREST);
        if (monitor) {
            MONITORINFO mi;
            mi.cbSize = sizeof(MONITORINFO);
            if (GetMonitorInfo(monitor, &mi)) {
                return (windowRect.left <= mi.rcMonitor.left &&
                        windowRect.top <= mi.rcMonitor.top &&
                        windowRect.right >= mi.rcMonitor.right &&
                        windowRect.bottom >= mi.rcMonitor.bottom);
            }
        }
    }
    catch (...) {
        return false;
    }

    return false;
}

int WindowStateManager::get_dpi_win32() {
    if (!m_initialized || !m_hwnd) return 96;

    try {
        // Try Windows 10 API first
        typedef UINT(WINAPI* GetDpiForWindow_t)(HWND);
        static auto GetDpiForWindow_fn =
            (GetDpiForWindow_t)GetProcAddress(GetModuleHandle(L"User32.dll"), "GetDpiForWindow");

        if (GetDpiForWindow_fn) {
            return GetDpiForWindow_fn(m_hwnd);
        }

        // Fallback to older API
        HDC hdc = GetDC(m_hwnd);
        if (hdc) {
            int dpi = GetDeviceCaps(hdc, LOGPIXELSX);
            ReleaseDC(m_hwnd, hdc);
            return dpi > 0 ? dpi : 96;
        }
    }
    catch (...) {
        return 96;
    }

    return 96;
}

WindowState WindowStateManager::get_window_state_win32() {
    if (!m_initialized || !m_hwnd) return WindowState::Normal;

    try {
        WINDOWPLACEMENT wp;
        wp.length = sizeof(WINDOWPLACEMENT);

        if (!GetWindowPlacement(m_hwnd, &wp)) {
            return WindowState::Normal;
        }

        if (wp.showCmd == SW_SHOWMINIMIZED) {
            return WindowState::Minimized;
        }
        else if (wp.showCmd == SW_SHOWMAXIMIZED) {
            return WindowState::Maximized;
        }

        if (check_fullscreen_win32()) {
            return WindowState::FullScreen;
        }
    }
    catch (...) {
        return WindowState::Normal;
    }

    return WindowState::Normal;
}

void WindowStateManager::update_state() {
    if (!m_initialized || !m_hwnd) return;

    std::lock_guard<std::recursive_mutex> lock(m_mutex);

    try {
        // Get window rectangle
        RECT windowRect;
        if (!GetWindowRect(m_hwnd, &windowRect)) {
            return;
        }

        // Get client rectangle
        RECT clientRect;
        if (!GetClientRect(m_hwnd, &clientRect)) {
            return;
        }

        // Update state
        m_current_state.screen_x = windowRect.left;
        m_current_state.screen_y = windowRect.top;
        m_current_state.width = windowRect.right - windowRect.left;
        m_current_state.height = windowRect.bottom - windowRect.top;
        m_current_state.client_width = clientRect.right;
        m_current_state.client_height = clientRect.bottom;
        m_current_state.state = get_window_state_win32();
        m_current_state.dpi = get_dpi_win32();
        m_current_state.scale_factor = static_cast<float>(m_current_state.dpi) / 96.0f;
        m_current_state.is_visible = IsWindowVisible(m_hwnd) != FALSE;
        m_current_state.is_focused = GetForegroundWindow() == m_hwnd;

        // Calculate client area screen position
        POINT pt = {0, 0};
        ClientToScreen(m_hwnd, &pt);
        m_current_state.client_x = pt.x;
        m_current_state.client_y = pt.y;

        // Get window title
        int length = GetWindowTextLength(m_hwnd);
        if (length > 0) {
            std::wstring title(length + 1, 0);
            GetWindowText(m_hwnd, title.data(), length + 1);
            int utf8_len = WideCharToMultiByte(CP_UTF8, 0, title.c_str(), -1, nullptr, 0, nullptr, nullptr);
            if (utf8_len > 0) {
                std::string utf8_title(utf8_len, 0);
                WideCharToMultiByte(CP_UTF8, 0, title.c_str(), -1, utf8_title.data(), utf8_len, nullptr, nullptr);
                m_current_state.title = utf8_title.c_str();
            }
        }
    }
    catch (const std::exception& e) {
        std::cerr << "WindowStateManager::update_state exception: " << e.what() << std::endl;
    }
    catch (...) {
        std::cerr << "WindowStateManager::update_state: Unknown exception" << std::endl;
    }
}

#else
// Non-Windows stub implementations

void WindowStateManager::initialize(void* hwnd) {
    m_initialized = false;
}

WindowPositionInfo WindowStateManager::get_window_position() {
    return m_current_state;
}

WindowState WindowStateManager::get_window_state() {
    return WindowState::Normal;
}

bool WindowStateManager::is_fullscreen() { return false; }
bool WindowStateManager::is_maximized() { return false; }
bool WindowStateManager::is_minimized() { return false; }
bool WindowStateManager::is_normal() { return true; }
int WindowStateManager::get_dpi() { return 96; }
float WindowStateManager::get_scale_factor() { return 1.0f; }
void WindowStateManager::screen_to_client(int& x, int& y) {}
void WindowStateManager::client_to_screen(int& x, int& y) {}
void WindowStateManager::update_state() {}

#endif

std::string WindowStateManager::export_to_json() {
    try {
        nlohmann::json j;

        j["screen_x"] = m_current_state.screen_x;
        j["screen_y"] = m_current_state.screen_y;
        j["client_x"] = m_current_state.client_x;
        j["client_y"] = m_current_state.client_y;
        j["width"] = m_current_state.width;
        j["height"] = m_current_state.height;
        j["client_width"] = m_current_state.client_width;
        j["client_height"] = m_current_state.client_height;

        std::string state_str;
        switch (m_current_state.state) {
        case WindowState::Normal: state_str = "normal"; break;
        case WindowState::Minimized: state_str = "minimized"; break;
        case WindowState::Maximized: state_str = "maximized"; break;
        case WindowState::FullScreen: state_str = "fullscreen"; break;
        }
        j["state"] = state_str;
        j["dpi"] = m_current_state.dpi;
        j["scale_factor"] = m_current_state.scale_factor;
        j["is_visible"] = m_current_state.is_visible;
        j["is_focused"] = m_current_state.is_focused;
        j["title"] = m_current_state.title;

        return j.dump(2);
    }
    catch (const std::exception& e) {
        std::cerr << "export_to_json exception: " << e.what() << std::endl;
        return "{}";
    }
}

bool WindowStateManager::export_to_file(const std::string& filepath) {
    try {
        std::string json = export_to_json();

        std::filesystem::path p(filepath);
        if (p.has_parent_path()) {
            std::filesystem::create_directories(p.parent_path());
        }

        std::ofstream file(filepath);
        if (file.is_open()) {
            file << json;
            file.close();
            return true;
        }
    }
    catch (const std::exception& e) {
        std::cerr << "export_to_file exception: " << e.what() << std::endl;
    }
    return false;
}

} // namespace Slic3r
