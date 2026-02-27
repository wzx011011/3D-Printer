#ifndef _WINDOWSTATEMANAGER_H
#define _WINDOWSTATEMANAGER_H

#include <string>
#include <mutex>

#ifdef _WIN32
#include <Windows.h>
#endif

namespace Slic3r {

enum class WindowState {
    Normal,
    Minimized,
    Maximized,
    FullScreen
};

struct WindowPositionInfo {
    int screen_x{0};
    int screen_y{0};
    int client_x{0};
    int client_y{0};
    int width{0};
    int height{0};
    int client_width{0};
    int client_height{0};
    WindowState state{WindowState::Normal};
    int dpi{96};
    float scale_factor{1.0f};
    bool is_visible{false};
    bool is_focused{false};
    std::string title;
};

class WindowStateManager {
public:
    static WindowStateManager& get_instance();

    void initialize(void* hwnd);
    bool is_initialized() const { return m_initialized; }

    WindowPositionInfo get_window_position();
    WindowState get_window_state();

    bool is_fullscreen();
    bool is_maximized();
    bool is_minimized();
    bool is_normal();

    int get_dpi();
    float get_scale_factor();

    void screen_to_client(int& x, int& y);
    void client_to_screen(int& x, int& y);

    WindowPositionInfo get_cached_state() const { return m_current_state; }
    void* get_window_handle() const { return m_hwnd; }

    std::string export_to_json();
    bool export_to_file(const std::string& filepath);

    void update_state();

private:
    WindowStateManager() = default;
    ~WindowStateManager() = default;
    WindowStateManager(const WindowStateManager&) = delete;
    WindowStateManager& operator=(const WindowStateManager&) = delete;

#ifdef _WIN32
    HWND m_hwnd{nullptr};
    bool check_fullscreen_win32();
    int get_dpi_win32();
    WindowState get_window_state_win32();
#endif

    WindowPositionInfo m_current_state;
    std::recursive_mutex m_mutex;
    bool m_initialized{false};
};

} // namespace Slic3r

#endif // _WINDOWSTATEMANAGER_H
