#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from typing import List, Dict, Tuple, Optional
import win32gui
import win32con
from PySide6.QtWidgets import QApplication, QLabel
from PySide6.QtCore import Qt
from PySide6.QtGui import QCursor


class WindowManager:
    """窗口管理器"""

    def __init__(self):
        self.bound_window: Optional[Dict] = None
        self.window_handle: Optional[int] = None
        self.window_rect: Optional[Tuple[int, int, int, int]] = None
        self.client_rect: Optional[Tuple[int, int, int, int]] = None

    def get_window_list(self) -> List[Dict]:
        """获取所有可见窗口列表"""
        windows = []

        def enum_windows_callback(hwnd, windows):
            if win32gui.IsWindowVisible(hwnd):
                window_text = win32gui.GetWindowText(hwnd)
                if window_text:  # 只显示有标题的窗口
                    class_name = win32gui.GetClassName(hwnd)
                    rect = win32gui.GetWindowRect(hwnd)
                    windows.append({
                        'handle': hwnd,
                        'title': window_text,
                        'class': class_name,
                        'rect': rect
                    })

        win32gui.EnumWindows(enum_windows_callback, windows)
        return windows

    def bind_window(self, window_handle: int) -> bool:
        """绑定窗口"""
        try:
            if win32gui.IsWindow(window_handle):
                self.window_handle = window_handle
                self.update_window_rect()
                self.bound_window = {
                    'handle': window_handle,
                    'title': win32gui.GetWindowText(window_handle),
                    'rect': self.window_rect,
                    'client_rect': self.client_rect
                }

                # 设置主窗口在绑定窗口之上
                self.set_main_window_above_bound_window()

                return True
        except Exception as e:
            print(f"绑定窗口失败: {e}")
        return False

    def set_main_window_above_bound_window(self):
        """设置绑定窗口在主窗口之下"""
        try:
            if self.window_handle and hasattr(self, 'winId'):
                # 获取主窗口句柄
                main_hwnd = self.winId()
                if main_hwnd:
                    # 直接将绑定窗口设置在主窗口之下
                    win32gui.SetWindowPos(
                        self.window_handle,  # 绑定窗口
                        main_hwnd,  # 主窗口句柄（作为参考窗口）
                        0, 0, 0, 0,  # 位置和大小保持不变
                        win32con.SWP_NOMOVE | win32con.SWP_NOSIZE | win32con.SWP_NOACTIVATE
                    )
                    print("绑定窗口已设置在主窗口之下")
        except Exception as e:
            print(f"设置窗口层级失败: {e}")

    def update_window_rect(self):
        """更新窗口位置信息"""
        if self.window_handle:
            # 获取窗口整体位置
            self.window_rect = win32gui.GetWindowRect(self.window_handle)
            # 获取客户区位置
            left, top, right, bottom = win32gui.GetClientRect(
                self.window_handle)
            client_left, client_top = win32gui.ClientToScreen(
                self.window_handle, (left, top))
            client_right, client_bottom = win32gui.ClientToScreen(
                self.window_handle, (right, bottom))
            self.client_rect = (
                client_left,
                client_top,
                client_right,
                client_bottom)

    def activate_window(self):
        """激活并置顶窗口"""
        if self.window_handle:
            try:
                # 如果窗口最小化，先恢复
                if win32gui.IsIconic(self.window_handle):
                    win32gui.ShowWindow(
                        self.window_handle, win32con.SW_RESTORE)

                # 将窗口置顶
                win32gui.SetForegroundWindow(self.window_handle)

                # 更新窗口位置信息
                self.update_window_rect()
            except Exception as e:
                print(f"激活窗口失败: {e}")

    def get_relative_coordinates(
            self, screen_x: int, screen_y: int) -> Tuple[int, int]:
        """将屏幕坐标转换为窗口客户区相对坐标"""
        if not self.client_rect:
            return screen_x, screen_y

        # 计算相对于客户区左上角的坐标
        rel_x = screen_x - self.client_rect[0]
        rel_y = screen_y - self.client_rect[1]

        # 计算相对百分比（0-1之间的值）
        width = self.client_rect[2] - self.client_rect[0]
        height = self.client_rect[3] - self.client_rect[1]
        if width > 0 and height > 0:
            rel_x = rel_x / width
            rel_y = rel_y / height

        return rel_x, rel_y

    def get_screen_coordinates(
            self, rel_x: float, rel_y: float) -> Tuple[int, int]:
        """将窗口相对坐标（百分比）转换为屏幕坐标"""
        if not self.client_rect:
            return int(rel_x), int(rel_y)

        # 更新窗口位置信息
        self.update_window_rect()

        # 计算客户区当前尺寸
        width = self.client_rect[2] - self.client_rect[0]
        height = self.client_rect[3] - self.client_rect[1]

        # 将百分比转换为实际坐标
        screen_x = int(self.client_rect[0] + (width * rel_x))
        screen_y = int(self.client_rect[1] + (height * rel_y))

        return screen_x, screen_y

    def is_window_active(self) -> bool:
        """检查绑定的窗口是否仍然有效"""
        if not self.window_handle:
            return False
        return bool(win32gui.IsWindow(self.window_handle))


class FloatingCoordLabel(QLabel):
    """悬浮坐标显示窗口"""

    def __init__(self):
        super().__init__()
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.Tool |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.SubWindow
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_OpaquePaintEvent, True)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground, True)

        self.setStyleSheet("""
            QLabel {
                background-color: rgba(0, 0, 0, 200);
                color: #00ff00;
                padding: 10px;
                border-radius: 6px;
                font-size: 18px;
                font-weight: bold;
                border: 2px solid #00ff00;
                font-family: 'Consolas', 'Microsoft YaHei', monospace;
            }
        """)

        # 预先创建固定大小
        self.setFixedSize(250, 50)  # 增加窗口大小
        self.hide()

    def update_position(
            self,
            rel_x: float,
            rel_y: float,
            screen_x: int,
            screen_y: int,
            status: str = ""):
        """更新位置和显示内容"""
        try:
            # 显示百分比坐标和状态
            status_text = f" - {status}" if status else ""
            coord_text = f"坐标: ({rel_x:.1%}, {rel_y:.1%}){status_text}"
            self.setText(
                f"<div style='text-shadow: 1px 1px 2px #000000;'>{coord_text}</div>")

            # 计算新位置（在光标右上角，考虑屏幕边界）
            screen_geo = QApplication.primaryScreen().geometry()
            cursor = QCursor.pos()

            # 默认位置：鼠标正上方偏右
            new_x = cursor.x()
            new_y = cursor.y() - self.height() - 20

            # 如果右边放不下，向左偏移
            if new_x + self.width() > screen_geo.width():
                new_x = cursor.x() - self.width()

            # 如果上面放不下，放到下面
            if new_y < 0:
                new_y = cursor.y() + 20

            self.move(new_x, new_y)

            if not self.isVisible():
                self.show()
        except Exception as e:
            print(f"Update position error: {e}") 