#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from typing import List, Tuple, Optional
from PySide6.QtCore import QObject, Signal, QTimer
from pynput.mouse import Button, Listener as MouseListener
from pynput.keyboard import Key, Listener as KeyboardListener

from window_manager import WindowManager, FloatingCoordLabel


class CoordinateCapture(QObject):
    """坐标捕获器"""

    # 添加信号用于线程安全的通信
    coordinate_captured = Signal(float, float)
    capture_cancelled = Signal()
    capture_restored = Signal()

    def __init__(self, window_manager: WindowManager):
        super().__init__()
        self.window_manager: WindowManager = window_manager
        self.capturing: bool = False
        self.mouse_listener: Optional[MouseListener] = None
        self.keyboard_listener: Optional[KeyboardListener] = None
        self.captured_coordinates: List[Tuple[float, float]] = []
        self.floating_label: Optional[FloatingCoordLabel] = None
        self.last_coordinates: Optional[Tuple[float, float, int, int]] = None
        self._current_pos: Optional[Tuple[int, int]] = None
        self._update_timer: QTimer = QTimer()
        self._update_timer.setInterval(33)
        self._update_timer.timeout.connect(self._update_label)

    def start_capture(self):
        """开始坐标捕获"""
        if not self.window_manager.bound_window:
            return False

        self.capturing = True

        # 创建悬浮窗
        if self.floating_label is None:
            self.floating_label = FloatingCoordLabel()

        # 启动鼠标监听
        self.mouse_listener = MouseListener(
            on_click=self._on_click,
            on_move=self._on_move
        )
        self.mouse_listener.start()

        # 启动键盘监听
        self.keyboard_listener = KeyboardListener(
            on_press=self._on_key_press
        )
        self.keyboard_listener.start()

        # 启动更新定时器
        self._update_timer.start()

        return True

    def stop_capture(self):
        """停止坐标捕获"""
        try:
            self._update_timer.stop()
            self.capturing = False

            if self.mouse_listener:
                self.mouse_listener.stop()
                self.mouse_listener = None

            if self.keyboard_listener:
                self.keyboard_listener.stop()
                self.keyboard_listener = None

            # 隐藏悬浮窗
            if self.floating_label:
                self.floating_label.hide()
                self.floating_label.deleteLater()
                self.floating_label = None

            # 发送恢复信号
            self.capture_restored.emit()
        except Exception as e:
            print(f"Stop capture error: {e}")

    def _on_click(self, x, y, button, pressed):
        """鼠标点击事件处理"""
        if pressed and button == Button.left and self.capturing:
            try:
                # 获取相对坐标
                rel_x, rel_y = self.window_manager.get_relative_coordinates(
                    x, y)
                self.captured_coordinates.append((rel_x, rel_y))

                # 停止定时器和监听器
                if self._update_timer.isActive():
                    self._update_timer.stop()
                self.capturing = False
                if self.mouse_listener:
                    self.mouse_listener.stop()
                    self.mouse_listener = None
                if self.keyboard_listener:
                    self.keyboard_listener.stop()
                    self.keyboard_listener = None

                # 隐藏悬浮窗（不删除，留给stop_capture处理）
                if self.floating_label:
                    self.floating_label.hide()

                # 使用信号发送坐标，确保线程安全
                self.coordinate_captured.emit(rel_x, rel_y)

                return False
            except Exception as e:
                print(f"Click handling error: {e}")
                self.capture_restored.emit()
                return False

    def _on_key_press(self, key):
        """键盘按键事件处理"""
        if key == Key.esc and self.capturing:
            try:
                self.stop_capture()
                if self.floating_label:
                    self.floating_label.hide()
                # 使用信号发送取消事件
                self.capture_cancelled.emit()
            except Exception as e:
                print(f"Key handling error: {e}")
            return False

    def _on_move(self, x, y):
        """鼠标移动事件处理"""
        if self.capturing:
            self._current_pos = (x, y)

    def _update_label(self):
        """定时更新标签位置和内容"""
        if not self.capturing or not self._current_pos or not self.floating_label:
            return

        try:
            x, y = self._current_pos
            rel_x, rel_y = self.window_manager.get_relative_coordinates(x, y)
            self.floating_label.update_position(rel_x, rel_y, x, y, "捕获中")
            self.last_coordinates = (rel_x, rel_y, x, y)
        except Exception as e:
            print(f"Update label error: {e}") 