#!/usr/bin/env python3
"""
UI 组件标注工具 - 先启动程序再截图标注
"""

import sys
import time
import subprocess
from pathlib import Path
import ctypes

try:
    import pyautogui
    from PIL import Image, ImageDraw, ImageFont
except ImportError:
    print("pip install pyautogui Pillow")
    sys.exit(1)

sys.path.insert(0, str(Path(__file__).parent))
from window_state import WindowStateMonitor, find_all_windows_by_title


def main():
    print("=" * 60)
    print("Creality Print UI 标注工具")
    print("=" * 60)

    # 程序路径
    app_path = Path(r"E:\wzx\C3DSlicer\C3DSlicer\build_unified\src\Release\CrealityPrint.exe")

    if not app_path.exists():
        print(f"程序不存在: {app_path}")
        return

    # 1. 启动程序
    print("\n[1] 启动 CrealityPrint...")

    # 先关闭已存在的进程
    subprocess.run(["taskkill", "/F", "/IM", "CrealityPrint.exe"],
                   capture_output=True, timeout=10)
    time.sleep(2)

    # 启动新进程
    proc = subprocess.Popen([str(app_path)])
    print(f"进程已启动: PID={proc.pid}")

    # 2. 等待窗口出现并完全加载
    print("\n[2] 等待窗口加载...")
    print("  等待30秒让程序完全启动...")

    target_hwnd = None

    for i in range(30):
        time.sleep(1)
        print(f"  检查中... ({i+1}s)")

        # 查找所有Creality窗口
        windows = find_all_windows_by_title("Creality")

        for hwnd in windows:
            try:
                monitor = WindowStateMonitor(hwnd)
                state = monitor.get_current_state()

                # 查找大窗口（主窗口通常很大）
                if state.width > 1000 and state.height > 800 and state.is_visible:
                    print(f"\n  找到主窗口: {hwnd}")
                    print(f"    标题: {state.title}")
                    print(f"    大小: {state.width} x {state.height}")
                    target_hwnd = hwnd
                    break
            except:
                continue

        if target_hwnd:
            break

    if not target_hwnd:
        print("未找到主窗口，尝试继续...")
        # 找任意Creality窗口
        windows = find_all_windows_by_title("Creality")
        if windows:
            target_hwnd = windows[0]
            print(f"使用窗口: {target_hwnd}")

    if not target_hwnd:
        print("错误: 未找到任何窗口")
        return

    # 额外等待UI稳定
    print("\n[3] 等待UI稳定...")
    time.sleep(10)

    # 3. 获取窗口状态
    print("\n[4] 获取窗口信息...")
    monitor = WindowStateMonitor(target_hwnd)
    state = monitor.get_current_state()

    print(f"  标题: {state.title}")
    print(f"  位置: ({state.screen_x}, {state.screen_y})")
    print(f"  大小: {state.width} x {state.height}")
    print(f"  DPI: {state.dpi}")
    print(f"  客户区: ({state.client_x}, {state.client_y})")

    if state.width < 100 or state.height < 100:
        print("\n错误: 窗口大小异常，请确保程序正常显示")
        return

    # 4. 截图
    print("\n[5] 截取窗口...")
    screenshot = pyautogui.screenshot(region=(
        state.screen_x, state.screen_y,
        state.width, state.height
    ))

    output_dir = Path(__file__).parent.parent / "screenshots"
    output_dir.mkdir(parents=True, exist_ok=True)

    raw_path = output_dir / "ui_raw.png"
    screenshot.save(raw_path)
    print(f"  原始截图: {raw_path}")

    # 5. 标注
    print("\n[6] 标注UI组件...")

    img = screenshot.copy()
    draw = ImageDraw.Draw(img)

    try:
        font = ImageFont.truetype("arial.ttf", 14)
        small_font = ImageFont.truetype("arial.ttf", 11)
    except:
        font = ImageFont.load_default()
        small_font = font

    # 客户区偏移
    offset_x = state.client_x - state.screen_x
    offset_y = state.client_y - state.screen_y
    print(f"  客户区偏移: ({offset_x}, {offset_y})")

    # UI组件定义（相对于客户区）
    components = [
        # 顶部菜单
        ("File", "menu", (10, 35, 50, 55)),
        ("Edit", "menu", (55, 35, 95, 55)),
        ("View", "menu", (100, 35, 140, 55)),
        ("Settings", "menu", (145, 35, 200, 55)),

        # 工具栏按钮
        ("New", "button", (210, 35, 245, 55)),
        ("Open", "button", (250, 35, 285, 55)),
        ("Save", "button", (290, 35, 325, 55)),
        ("Undo", "button", (335, 35, 365, 55)),
        ("Redo", "button", (370, 35, 400, 55)),

        # 主标签页
        ("Prepare", "tab", (420, 8, 540, 32)),
        ("Preview", "tab", (550, 8, 670, 32)),
        ("Device", "tab", (680, 8, 800, 32)),

        # 左侧面板
        ("Left Panel", "panel", (5, 60, 280, 400)),
        ("Model List", "list", (15, 80, 270, 380)),

        # 中间3D区域
        ("3D Canvas", "canvas", (285, 60, 1550, 920)),

        # 右侧设置面板
        ("Right Panel", "panel", (1555, 60, 1905, 920)),
        ("Print Settings", "section", (1565, 75, 1895, 200)),
        ("Quality", "section", (1565, 210, 1895, 350)),
        ("Infill", "section", (1565, 360, 1895, 500)),
        ("Support", "section", (1565, 510, 1895, 650)),

        # 底部
        ("Slice Button", "button", (800, 930, 1050, 975)),
        ("Preview Gcode", "button", (1070, 930, 1350, 975)),
        ("Status Bar", "status", (0, 1000, 1920, 1033)),
    ]

    colors = {
        'button': '#FF6B6B',
        'menu': '#4ECDC4',
        'tab': '#96CEB4',
        'panel': '#FFEAA7',
        'section': '#DDA0DD',
        'canvas': '#87CEEB',
        'list': '#98D8C8',
        'status': '#C0C0C0',
    }

    drawn_count = 0
    for i, (name, ctype, rect) in enumerate(components):
        x1 = rect[0] + offset_x
        y1 = rect[1] + offset_y
        x2 = rect[2] + offset_x
        y2 = rect[3] + offset_y

        # 跳过超出范围的
        if x2 > img.width or y2 > img.height or x1 < 0 or y1 < 0:
            continue

        color = colors.get(ctype, '#808080')

        # 画框
        draw.rectangle([x1, y1, x2, y2], outline=color, width=2)

        # 画标签
        label = f"{drawn_count+1}.{name}"
        bbox = draw.textbbox((x1, y1-16), label, font=small_font)
        draw.rectangle([bbox[0]-2, bbox[1]-1, bbox[2]+2, bbox[3]+1], fill=color)
        draw.text((x1, y1-16), label, fill='white', font=small_font)

        drawn_count += 1

    # 添加图例
    legend_x = img.width - 110
    legend_y = 30
    draw.rectangle([legend_x-10, legend_y-10, img.width-10, legend_y+90],
                   fill='white', outline='black')

    for i, (ctype, color) in enumerate(colors.items()):
        y = legend_y + i * 18
        draw.rectangle([legend_x, y, legend_x+12, y+10], fill=color, outline='black')
        draw.text((legend_x+16, y-2), ctype, fill='black', font=small_font)

    # 保存
    annotated_path = output_dir / "ui_annotated.png"
    img.save(annotated_path)
    print(f"  标注截图: {annotated_path}")

    # 6. 输出组件列表
    print("\n" + "=" * 60)
    print("UI 组件列表")
    print("=" * 60)

    count = 0
    for name, ctype, rect in components:
        x1 = rect[0] + offset_x
        y1 = rect[1] + offset_y
        x2 = rect[2] + offset_x
        y2 = rect[3] + offset_y

        if x2 > img.width or y2 > img.height:
            continue

        print(f"  [{count+1}] {name} ({ctype})")
        print(f"      客户区: ({rect[0]}, {rect[1]}) - ({rect[2]}, {rect[3]})")
        print(f"      尺寸: {rect[2]-rect[0]} x {rect[3]-rect[1]}")
        count += 1

    print("\n" + "=" * 60)
    print("完成!")
    print(f"  原始: {raw_path}")
    print(f"  标注: {annotated_path}")
    print("=" * 60)


if __name__ == '__main__':
    main()
