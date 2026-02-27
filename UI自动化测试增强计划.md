# UI自动化测试增强计划 - 窗口状态检测与位置感知点击

## Context

### 问题背景
当前自动化测试存在以下问题：
1. 运行自动化测试时VSCode会被关闭（已在 `AutomationMgr.cpp` 中暂时禁用 `TerminateProcess`）
2. 缺少窗口状态检测（全屏、最大化、最小化）
3. 缺少DPI缩放处理，导致高分屏上点击位置不准确
4. UI组件位置会随窗口状态变化而变化，影响自动化测试的稳定性

### 用户需求
- 通过代码检测各个UI组件的位置
- 检测软件位置和全屏状态等会影响控件位置的因素
- 触发UI的点击等鼠标和键盘事件

### 现有基础设施
- **C++层**: `src/libslic3r/AutomationMgr.cpp/hpp` - 基础自动化管理
- **Python层**: `.claude/skills/slice-test/scripts/gui_automation.py` - 使用pywinauto的GUI自动化框架
- **参考**: `src/slic3r/GUI/GUI_Utils.hpp` - 已有DPIFrame和WindowMetrics类

---

## Implementation Plan

### Phase 1: Python层窗口状态检测模块（独立可用）

#### 1.1 创建 `window_state.py` 模块
**文件**: `.claude/skills/slice-test/scripts/window_state.py`

实现功能：
- `WindowStateEnum` - 窗口状态枚举 (normal/minimized/maximized/fullscreen)
- `WindowInfo` - 窗口信息数据类（位置、大小、DPI等）
- `WindowStateMonitor` - 窗口状态监控器，使用Windows API检测：
  - 全屏状态检测（比较窗口与显示器大小，检查窗口样式）
  - 最大化/最小化状态（IsZoomed/IsIconic）
  - DPI获取（GetDpiForWindow）
  - 坐标转换（ScreenToClient/ClientToScreen）
- `PositionAwareClicker` - 位置感知点击器

#### 1.2 扩展 `gui_automation.py`
**文件**: `.claude/skills/slice-test/scripts/gui_automation.py`

添加功能：
- `window_state` 属性 - 获取当前窗口状态
- `is_fullscreen()` / `is_maximized()` / `is_minimized()` 方法
- `get_dpi()` / `get_scale_factor()` 方法
- `screen_to_client()` / `client_to_screen()` 坐标转换
- `click_element_adaptive()` - 自适应点击（考虑窗口状态和DPI）
- `get_element_center()` - 获取元素中心屏幕坐标
- `verify_element_position()` - 验证元素位置

---

### Phase 2: 测试运行器扩展

#### 2.1 扩展 `gui_test_runner.py`
**文件**: `.claude/skills/slice-test/scripts/gui_test_runner.py`

添加新的动作处理器：
| 动作 | 说明 |
|------|------|
| `verify_window_state` | 验证窗口状态 |
| `get_dpi_info` | 获取DPI信息 |
| `maximize_window` | 最大化窗口 |
| `minimize_window` | 最小化窗口 |
| `restore_window` | 恢复窗口 |
| `verify_element_position` | 验证元素位置 |
| `verify_coordinate_conversion` | 验证坐标转换 |

#### 2.2 创建测试用例
**文件**: `.claude/skills/slice-test/config/test_cases/window_state_tests.yaml`

测试用例：
- WINSTATE-001: 正常窗口模式UI组件位置验证
- WINSTATE-002: 最大化模式UI组件位置验证
- WINSTATE-003: DPI缩放检测
- WINSTATE-004: 窗口恢复测试
- WINSTATE-005: 坐标转换验证

---

### Phase 3: C++层扩展（可选，用于更深集成）

#### 3.1 创建 `WindowStateManager` 类
**新文件**: `src/libslic3r/WindowStateManager.hpp` 和 `.cpp`

功能：
- 窗口状态检测（使用Windows API）
- DPI缩放因子获取
- 坐标转换
- 状态导出为JSON（供Python层读取）

#### 3.2 扩展 `AutomationMgr`
**文件**: `src/libslic3r/AutomationMgr.cpp/hpp`

添加方法：
- `exportWindowState()` - 导出窗口状态到JSON文件
- `getWindowStateJson()` - 获取窗口状态JSON字符串

#### 3.3 集成到主窗口
**文件**: `src/slic3r/GUI/MainFrame.cpp`

在窗口初始化时调用 `WindowStateManager::initialize()`

---

## Critical Files

| 文件 | 修改类型 | 优先级 |
|------|----------|--------|
| `.claude/skills/slice-test/scripts/window_state.py` | 新增 | 高 |
| `.claude/skills/slice-test/scripts/gui_automation.py` | 修改 | 高 |
| `.claude/skills/slice-test/scripts/gui_test_runner.py` | 修改 | 中 |
| `.claude/skills/slice-test/config/test_cases/window_state_tests.yaml` | 新增 | 中 |
| `src/libslic3r/WindowStateManager.hpp` | 新增 | 低 |
| `src/libslic3r/WindowStateManager.cpp` | 新增 | 低 |
| `src/libslic3r/AutomationMgr.hpp` | 修改 | 低 |
| `src/libslic3r/AutomationMgr.cpp` | 修改 | 低 |

---

## Key Implementation Details

### 窗口状态检测核心逻辑（Python）
```python
def is_fullscreen(self) -> bool:
    # 1. 检查窗口样式（无边框=可能全屏）
    style = GetWindowLongPtrW(hwnd, GWL_STYLE)
    has_border = (style & WS_CAPTION) or (style & WS_THICKFRAME)

    # 2. 比较窗口与显示器大小
    monitor = MonitorFromWindow(hwnd, MONITOR_DEFAULTTONEAREST)
    GetMonitorInfo(monitor, &mi)

    return not has_border and window_rect covers monitor_rect
```

### 坐标转换
```python
def client_to_screen(self, client_x, client_y):
    # 客户端坐标 + 客户端区域屏幕位置 = 屏幕坐标
    return (client_x + state.client_rect[0], client_y + state.client_rect[1])
```

### 自适应点击流程
```
1. 获取窗口状态
2. 如果最小化 -> 恢复窗口
3. 等待窗口状态稳定
4. 获取元素屏幕坐标
5. 考虑DPI缩放
6. 执行点击
```

---

## Verification

### 单元测试
1. 运行 `python window_state.py` 验证窗口检测功能
2. 启动Creality Print，验证能正确检测窗口状态

### 集成测试
```bash
cd .claude/skills/slice-test/scripts
python run_tests.py --test-case WINSTATE-001
python run_tests.py --test-case WINSTATE-002
```

### 手动验证
1. 在不同窗口模式下（正常/最大化/全屏）运行测试
2. 在高分屏（DPI > 96）上验证点击位置准确
3. 验证最小化恢复后点击仍然有效

---

## Dependencies
- Python: pywinauto, pyautogui, ctypes (Windows)
- C++: nlohmann/json, Windows API (User32.dll, Shcore.dll)
