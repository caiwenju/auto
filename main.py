#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import time
import json
import os
from typing import List, Dict, Tuple

from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                               QHBoxLayout, QGridLayout, QLabel, QPushButton,
                               QListWidget, QListWidgetItem, QComboBox,
                               QGroupBox, QMessageBox, QInputDialog,
                               QLineEdit, QDialog, QDoubleSpinBox,
                               QFileDialog, QTabWidget, QScrollArea, QCheckBox,
                               )
from PySide6.QtCore import Qt, QThread, Signal, QTimer, QObject, QEvent
import win32gui
import win32api
import win32con
from pynput.mouse import Button, Listener as MouseListener
from pynput.keyboard import Key, Listener as KeyboardListener
from PySide6.QtGui import QCursor


class WindowManager:
    """窗口管理器"""

    def __init__(self):
        self.bound_window = None
        self.window_handle = None
        self.window_rect = None
        self.client_rect = None

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
                return True
        except Exception as e:
            print(f"绑定窗口失败: {e}")
        return False

    def update_window_rect(self):
        """更新窗口位置信息"""
        if self.window_handle:
            # 获取窗口整体位置
            self.window_rect = win32gui.GetWindowRect(self.window_handle)
            # 获取客户区位置
            left, top, right, bottom = win32gui.GetClientRect(self.window_handle)
            client_left, client_top = win32gui.ClientToScreen(self.window_handle, (left, top))
            client_right, client_bottom = win32gui.ClientToScreen(self.window_handle, (right, bottom))
            self.client_rect = (client_left, client_top, client_right, client_bottom)

    def activate_window(self):
        """激活并置顶窗口"""
        if self.window_handle:
            try:
                # 如果窗口最小化，先恢复
                if win32gui.IsIconic(self.window_handle):
                    win32gui.ShowWindow(self.window_handle, win32con.SW_RESTORE)

                # 将窗口置顶
                win32gui.SetForegroundWindow(self.window_handle)

                # 更新窗口位置信息
                self.update_window_rect()
            except Exception as e:
                print(f"激活窗口失败: {e}")

    def get_relative_coordinates(self, screen_x: int, screen_y: int) -> Tuple[int, int]:
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

    def get_screen_coordinates(self, rel_x: float, rel_y: float) -> Tuple[int, int]:
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
        return win32gui.IsWindow(self.window_handle)


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

    def update_position(self, rel_x: float, rel_y: float, screen_x: int, screen_y: int, status: str = ""):
        """更新位置和显示内容"""
        try:
            # 显示百分比坐标和状态
            status_text = f" - {status}" if status else ""
            coord_text = f"坐标: ({rel_x:.1%}, {rel_y:.1%}){status_text}"
            self.setText(f"<div style='text-shadow: 1px 1px 2px #000000;'>{coord_text}</div>")

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


class CoordinateCapture(QObject):
    """坐标捕获器"""

    # 添加信号用于线程安全的通信
    coordinate_captured = Signal(float, float)
    capture_cancelled = Signal()
    capture_restored = Signal()

    def __init__(self, window_manager: WindowManager):
        super().__init__()
        self.window_manager = window_manager  # 修复：使用传入的window_manager而不是创建新的
        self.capturing = False
        self.mouse_listener = None
        self.keyboard_listener = None
        self.captured_coordinates = []
        self.floating_label = None
        self.last_coordinates = None
        self._current_pos = None
        self._update_timer = QTimer()
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
                rel_x, rel_y = self.window_manager.get_relative_coordinates(x, y)
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


class AutomationStep:
    """自动化步骤类"""

    def __init__(self, x: float = 0.0, y: float = 0.0, action: str = "左键单击", delay: float = 0.0, text: str = ""):
        self.x = x  # 相对坐标（百分比）
        self.y = y  # 相对坐标（百分比）
        self.action = action
        self.delay = delay
        self.text = text

    def to_dict(self) -> Dict:
        """转换为字典"""
        return {
            'x': self.x,
            'y': self.y,
            'action': self.action,
            'delay': self.delay,
            'text': self.text
        }

    @classmethod
    def from_dict(cls, data: Dict) -> 'AutomationStep':
        """从字典创建实例"""
        return cls(
            x=float(data.get('x', 0.0)),
            y=float(data.get('y', 0.0)),
            action=data.get('action', '左键单击'),
            delay=float(data.get('delay', 0.0)),
            text=data.get('text', '')
        )


class AutomationExecutor(QThread):
    """自动化执行器"""

    step_completed = Signal(int, str)  # 步骤完成信号
    execution_finished = Signal(bool, str)  # 执行完成信号
    progress_updated = Signal(int)  # 进度更新信号

    def __init__(self, steps: List[AutomationStep], window_manager: WindowManager):
        super().__init__()
        self.steps = steps
        self.window_manager = window_manager
        self.running = False
        self.paused = False

    def run(self):
        """执行自动化步骤"""
        self.running = True
        self.paused = False

        try:
            for i, step in enumerate(self.steps):
                if not self.running:
                    break

                # 等待暂停状态结束
                while self.paused and self.running:
                    time.sleep(0.1)

                if not self.running:
                    break

                # 执行步骤
                success = self._execute_step(step)
                if success:
                    self.step_completed.emit(i + 1, f"步骤 {i + 1} 执行成功")
                else:
                    self.step_completed.emit(i + 1, f"步骤 {i + 1} 执行失败")
                    break

                # 更新进度
                progress = int((i + 1) / len(self.steps) * 100)
                self.progress_updated.emit(progress)

                # 延迟
                if step.delay > 0:
                    time.sleep(step.delay)

            if self.running:
                self.execution_finished.emit(True, "所有步骤执行完成")
            else:
                self.execution_finished.emit(False, "执行被用户停止")

        except Exception as e:
            self.execution_finished.emit(False, f"执行出错: {str(e)}")
        finally:
            self.running = False

    def _execute_step(self, step: AutomationStep) -> bool:
        """执行单个步骤"""
        try:
            # 获取屏幕坐标
            screen_x, screen_y = self.window_manager.get_screen_coordinates(step.x, step.y)

            # 移动鼠标到目标位置
            win32api.SetCursorPos((screen_x, screen_y))
            time.sleep(0.1)  # 短暂延迟确保鼠标移动到位

            # 执行相应的动作
            if step.action == "左键单击":
                win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, screen_x, screen_y, 0, 0)
                win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, screen_x, screen_y, 0, 0)
            elif step.action == "右键单击":
                win32api.mouse_event(win32con.MOUSEEVENTF_RIGHTDOWN, screen_x, screen_y, 0, 0)
                win32api.mouse_event(win32con.MOUSEEVENTF_RIGHTUP, screen_x, screen_y, 0, 0)
            elif step.action == "双击":
                win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, screen_x, screen_y, 0, 0)
                win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, screen_x, screen_y, 0, 0)
                time.sleep(0.05)
                win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, screen_x, screen_y, 0, 0)
                win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, screen_x, screen_y, 0, 0)
            elif step.action == "输入文本" and step.text:
                # 这里可以添加文本输入功能
                pass

            return True

        except Exception as e:
            print(f"执行步骤失败: {e}")
            return False

    def pause(self):
        """暂停执行"""
        self.paused = True

    def resume(self):
        """恢复执行"""
        self.paused = False

    def stop(self):
        """停止执行"""
        self.running = False
        self.paused = False


class AutomationFeature:
    """自动化功能类"""

    def __init__(self, name: str, steps: List[AutomationStep]):
        self.name = name
        self.steps = steps

    def to_dict(self) -> Dict:
        """转换为字典"""
        return {
            'name': self.name,
            'steps': [step.to_dict() for step in self.steps]
        }

    @classmethod
    def from_dict(cls, data: Dict) -> 'AutomationFeature':
        """从字典创建实例"""
        return cls(
            name=data['name'],
            steps=[AutomationStep.from_dict(step) for step in data['steps']]
        )


class FeatureManager:
    """功能管理器"""

    def __init__(self):
        self.features: List[AutomationFeature] = []
        self.data_file = "automation_features.json"
        self.load_features()

    def load_features(self):
        """加载功能列表"""
        try:
            if os.path.exists(self.data_file):
                with open(self.data_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.features = [AutomationFeature.from_dict(feature) for feature in data]
        except Exception as e:
            print(f"加载功能列表失败: {e}")
            self.features = []

    def save_features(self):
        """保存功能列表"""
        try:
            data = [feature.to_dict() for feature in self.features]
            with open(self.data_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"保存功能列表失败: {e}")

    def add_feature(self, feature: AutomationFeature):
        """添加功能"""
        self.features.append(feature)
        self.save_features()

    def update_feature(self, index: int, feature: AutomationFeature):
        """更新功能"""
        if 0 <= index < len(self.features):
            self.features[index] = feature
            self.save_features()

    def delete_feature(self, index: int):
        """删除功能"""
        if 0 <= index < len(self.features):
            del self.features[index]
            self.save_features()


class StepListWidget(QListWidget):
    """自定义步骤列表控件"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setSpacing(2)  # 设置项目间距
        self.parent = parent

    def add_step_item(self, step: AutomationStep, index: int):
        """添加步骤项"""
        item = QListWidgetItem(self)
        widget = StepItemWidget(step, index, self.parent)
        item.setSizeHint(widget.sizeHint())
        self.addItem(item)
        self.setItemWidget(item, widget)

    def dropEvent(self, event):
        """处理拖拽放置事件"""
        super().dropEvent(event)
        # 拖拽完成后通知父窗口更新步骤顺序
        if hasattr(self.parent, 'update_steps_order_after_drag'):
            self.parent.update_steps_order_after_drag()


class StepItemWidget(QWidget):
    """步骤项控件"""

    def __init__(self, step: AutomationStep, index: int, parent=None):
        super().__init__()
        self.step = step
        self.index = index
        self.parent = parent
        self.init_ui()

    def init_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(5, 2, 5, 2)

        # 步骤信息
        step_text = f"步骤 {self.index + 1}: ({self.step.x:.1%}, {self.step.y:.1%}) - {self.step.action}"
        if self.step.delay > 0:
            step_text += f" [延迟: {self.step.delay}s]"
        if self.step.text:
            step_text += f" [文本: {self.step.text}]"
        info_label = QLabel(step_text)
        layout.addWidget(info_label)

        layout.addStretch()

        # 编辑按钮
        edit_btn = QPushButton("✏")
        edit_btn.setFixedSize(28, 28)
        edit_btn.setObjectName("stepEditBtn")
        edit_btn.setStyleSheet("""
            QPushButton#stepEditBtn {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, 
                    stop:0 #f8f9fa, stop:1 #e9ecef) !important;
                border: 1px solid #dee2e6 !important;
                border-radius: 14px !important;
                color: #495057 !important;
                font-size: 14px !important;
                font-weight: normal !important;
                padding: 0px !important;
            }
            QPushButton#stepEditBtn:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, 
                    stop:0 #e3f2fd, stop:1 #bbdefb) !important;
                border-color: #2196f3 !important;
                color: #1976d2 !important;
            }
            QPushButton#stepEditBtn:pressed {
                background: #90caf9 !important;
                border-color: #1976d2 !important;
            }
        """)
        # 确保父组件是MainWindow或包含edit_step方法的类
        if hasattr(self.parent, 'edit_step'):
            edit_btn.clicked.connect(lambda: self.parent.edit_step(self.index))
        layout.addWidget(edit_btn)

        # 删除按钮
        delete_btn = QPushButton("×")
        delete_btn.setFixedSize(28, 28)
        delete_btn.setObjectName("stepDeleteBtn")
        delete_btn.setStyleSheet("""
            QPushButton#stepDeleteBtn {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, 
                    stop:0 #fff5f5, stop:1 #fed7d7) !important;
                border: 1px solid #feb2b2 !important;
                border-radius: 14px !important;
                color: #c53030 !important;
                font-size: 16px !important;
                font-weight: bold !important;
                padding: 0px !important;
            }
            QPushButton#stepDeleteBtn:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, 
                    stop:0 #fed7d7, stop:1 #fc8181) !important;
                border-color: #f56565 !important;
                color: #9b2c2c !important;
            }
            QPushButton#stepDeleteBtn:pressed {
                background: #fc8181 !important;
                border-color: #e53e3e !important;
            }
        """)
        # 确保父组件是MainWindow或包含delete_step方法的类
        if hasattr(self.parent, 'delete_step'):
            delete_btn.clicked.connect(lambda: self.parent.delete_step(self.index))
        layout.addWidget(delete_btn)


class FeatureCard(QWidget):
    """功能卡片组件"""

    def __init__(self, feature: AutomationFeature, index: int, parent=None):
        super().__init__()
        self.feature = feature
        self.index = index
        self.parent = parent
        self.status = "停止"  # 默认状态：停止、运行中、暂停、错误
        self.is_selected = False
        self.is_hovered = False
        self.init_ui()

    def init_ui(self):
        # 设置卡片样式
        self.setObjectName("featureCard")
        self.update_card_style()

        # 创建主布局
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(12, 12, 12, 12)
        main_layout.setSpacing(8)

        # 顶部区域：功能名称和选择框
        top_layout = QHBoxLayout()

        # 选择框
        self.checkbox = QCheckBox()
        self.checkbox.setFixedSize(20, 20)
        self.checkbox.stateChanged.connect(self.on_checkbox_changed)
        top_layout.addWidget(self.checkbox)

        # 功能名称
        name_label = QLabel(self.feature.name)
        name_label.setStyleSheet("font-size: 16px; font-weight: bold; color: #212529;")
        top_layout.addWidget(name_label)

        # 状态指示器
        self.status_label = QLabel(self.status)
        self.status_label.setStyleSheet(
            "color: #6c757d; font-size: 12px; padding: 2px 6px; border-radius: 4px; background-color: #f8f9fa;")
        top_layout.addWidget(self.status_label)

        top_layout.addStretch()
        main_layout.addLayout(top_layout)

        # 中间区域：步骤信息
        info_layout = QHBoxLayout()
        steps_info = QLabel(f"{len(self.feature.steps)} 个步骤")
        steps_info.setStyleSheet("color: #6c757d; font-size: 13px;")
        info_layout.addWidget(steps_info)
        info_layout.addStretch()
        main_layout.addLayout(info_layout)

        # 底部区域：操作按钮
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        # 执行按钮
        self.run_btn = QPushButton("执行")
        self.run_btn.setObjectName("cardRunBtn")
        self.run_btn.setFixedSize(60, 28)
        self.run_btn.setStyleSheet("""
            QPushButton#cardRunBtn {
                background-color: #007bff;
                color: white;
                border: none;
                border-radius: 4px;
                font-size: 12px;
            }
            QPushButton#cardRunBtn:hover {
                background-color: #0069d9;
            }
            QPushButton#cardRunBtn:pressed {
                background-color: #0062cc;
            }
        """)
        self.run_btn.clicked.connect(lambda: self.parent.run_feature(self.index))
        button_layout.addWidget(self.run_btn)

        # 暂停按钮
        self.pause_btn = QPushButton("暂停")
        self.pause_btn.setObjectName("cardPauseBtn")
        self.pause_btn.setFixedSize(60, 28)
        self.pause_btn.setStyleSheet("""
            QPushButton#cardPauseBtn {
                background-color: #ffc107;
                color: #212529;
                border: none;
                border-radius: 4px;
                font-size: 12px;
            }
            QPushButton#cardPauseBtn:hover {
                background-color: #e0a800;
            }
            QPushButton#cardPauseBtn:pressed {
                background-color: #d39e00;
            }
        """)
        self.pause_btn.clicked.connect(lambda: self.parent.pause_feature(self.index))
        self.pause_btn.setEnabled(False)  # 初始状态禁用
        button_layout.addWidget(self.pause_btn)

        # 编辑按钮
        self.edit_btn = QPushButton("编辑")
        self.edit_btn.setObjectName("cardEditBtn")
        self.edit_btn.setFixedSize(60, 28)
        self.edit_btn.setStyleSheet("""
            QPushButton#cardEditBtn {
                background-color: #6c757d;
                color: white;
                border: none;
                border-radius: 4px;
                font-size: 12px;
            }
            QPushButton#cardEditBtn:hover {
                background-color: #5a6268;
            }
            QPushButton#cardEditBtn:pressed {
                background-color: #545b62;
            }
        """)
        self.edit_btn.clicked.connect(lambda: self.parent.edit_feature_by_index(self.index))
        button_layout.addWidget(self.edit_btn)

        # 删除按钮
        self.delete_btn = QPushButton("删除")
        self.delete_btn.setObjectName("cardDeleteBtn")
        self.delete_btn.setFixedSize(60, 28)
        self.delete_btn.setStyleSheet("""
            QPushButton#cardDeleteBtn {
                background-color: #dc3545;
                color: white;
                border: none;
                border-radius: 4px;
                font-size: 12px;
            }
            QPushButton#cardDeleteBtn:hover {
                background-color: #c82333;
            }
            QPushButton#cardDeleteBtn:pressed {
                background-color: #bd2130;
            }
        """)
        self.delete_btn.clicked.connect(lambda: self.parent.delete_feature_by_index(self.index))
        button_layout.addWidget(self.delete_btn)

        main_layout.addLayout(button_layout)

        # 添加鼠标点击事件
        self.mousePressEvent = self.on_card_clicked

        # 安装事件过滤器处理悬停
        self.installEventFilter(self)

    def eventFilter(self, obj, event):
        """事件过滤器，处理鼠标悬停事件"""
        if obj == self:
            if event.type() == QEvent.Type.Enter:
                self.is_hovered = True
                self.update_card_style()
                return True
            elif event.type() == QEvent.Type.Leave:
                self.is_hovered = False
                self.update_card_style()
                return True
        return super().eventFilter(obj, event)

    def update_card_style(self):
        """更新卡片样式"""
        if self.is_selected:
            if self.is_hovered:
                self.setStyleSheet("""
                    QWidget#featureCard {
                        background-color: #e3f2fd;
                        border-radius: 8px;
                        border: 1px solid #64b5f6;
                        box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1);
                    }
                """)
            else:
                self.setStyleSheet("""
                    QWidget#featureCard {
                        background-color: #e3f2fd;
                        border-radius: 8px;
                        border: 1px solid #90caf9;
                    }
                """)
        else:
            if self.is_hovered:
                self.setStyleSheet("""
                    QWidget#featureCard {
                        background-color: #f8f9fa;
                        border-radius: 8px;
                        border: 1px solid #90caf9;
                        box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1);
                    }
                """)
            else:
                self.setStyleSheet("""
                    QWidget#featureCard {
                        background-color: white;
                        border-radius: 8px;
                        border: 1px solid #e0e0e0;
                    }
                """)

    def on_card_clicked(self, event):
        """卡片点击事件处理"""
        # 切换选中状态
        self.set_selected(not self.is_selected)
        # 更新批量按钮状态
        if hasattr(self.parent, 'update_batch_buttons_state'):
            self.parent.update_batch_buttons_state()

    def on_checkbox_changed(self, state):
        """复选框状态变化处理"""
        self.is_selected = (state == Qt.CheckState.Checked)
        self.update_card_style()
        # 更新批量按钮状态
        if hasattr(self.parent, 'update_batch_buttons_state'):
            self.parent.update_batch_buttons_state()

    def set_status(self, status: str):
        """设置功能状态"""
        self.status = status
        self.status_label.setText(status)

        # 根据状态更新样式
        if status == "运行中":
            self.status_label.setStyleSheet(
                "color: white; font-size: 12px; padding: 2px 6px; border-radius: 4px; background-color: #28a745;")
            self.run_btn.setEnabled(False)
            self.pause_btn.setEnabled(True)
        elif status == "暂停":
            self.status_label.setStyleSheet(
                "color: #212529; font-size: 12px; padding: 2px 6px; border-radius: 4px; background-color: #ffc107;")
            self.run_btn.setEnabled(True)
            self.pause_btn.setEnabled(True)
        elif status == "错误":
            self.status_label.setStyleSheet(
                "color: white; font-size: 12px; padding: 2px 6px; border-radius: 4px; background-color: #dc3545;")
            self.run_btn.setEnabled(True)
            self.pause_btn.setEnabled(False)
        else:  # 停止
            self.status_label.setStyleSheet(
                "color: #6c757d; font-size: 12px; padding: 2px 6px; border-radius: 4px; background-color: #f8f9fa;")
            self.run_btn.setEnabled(True)
            self.pause_btn.setEnabled(False)

    def set_selected(self, selected: bool):
        """设置选中状态"""
        self.is_selected = selected
        self.checkbox.setChecked(selected)
        self.update_card_style()


class FeatureDialog(QDialog):
    """功能编辑对话框"""

    def __init__(self, parent=None, feature: AutomationFeature = None):
        super().__init__(parent)
        self.feature = feature
        self.steps = (feature.steps.copy() if feature else [])

        # 设置窗口标志
        self.setWindowFlags(
            Qt.WindowType.Dialog |
            Qt.WindowType.WindowStaysOnTopHint
        )

        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("编辑功能")
        self.setModal(True)
        self.resize(600, 500)

        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        layout.setContentsMargins(15, 15, 15, 15)

        # 功能名称
        name_layout = QHBoxLayout()
        name_layout.addWidget(QLabel("功能名称:"))
        self.name_edit = QLineEdit()
        self.name_edit.setFixedHeight(32)
        if self.feature:
            self.name_edit.setText(self.feature.name)
        name_layout.addWidget(self.name_edit)
        layout.addLayout(name_layout)

        # 步骤列表标题
        steps_label = QLabel("步骤列表（可拖拽调整顺序）:")
        steps_label.setStyleSheet("font-weight: bold; margin-top: 10px;")
        layout.addWidget(steps_label)

        # 步骤列表（支持拖拽）
        self.steps_list = StepListWidget(self)
        self.steps_list.setDragDropMode(QListWidget.DragDropMode.InternalMove)
        self.update_steps_list()
        layout.addWidget(self.steps_list)

        # 按钮区域
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        self.ok_button = QPushButton("确定")
        self.ok_button.setFixedHeight(36)
        self.ok_button.setObjectName("featureOkBtn")
        self.ok_button.setStyleSheet("""
            QPushButton#featureOkBtn {
                background-color: #28a745 !important;
                border: none !important;
                color: white !important;
                font-size: 13px !important;
                padding: 8px 20px !important;
                border-radius: 6px !important;
            }
            QPushButton#featureOkBtn:hover {
                background-color: #218838 !important;
            }
        """)
        self.ok_button.clicked.connect(self.accept)

        self.cancel_button = QPushButton("取消")
        self.cancel_button.setFixedHeight(36)
        self.cancel_button.setFixedWidth(80)
        self.cancel_button.setObjectName("featureCancelBtn")
        self.cancel_button.setStyleSheet("""
            QPushButton#featureCancelBtn {
                background-color: #6c757d !important;
                border: none !important;
                color: white !important;
                font-size: 13px !important;
                padding: 8px 16px !important;
                border-radius: 6px !important;
            }
            QPushButton#featureCancelBtn:hover {
                background-color: #5a6268 !important;
            }
        """)
        self.cancel_button.clicked.connect(self.reject)

        button_layout.addWidget(self.ok_button)
        button_layout.addWidget(self.cancel_button)
        layout.addLayout(button_layout)

    def update_steps_list(self):
        """更新步骤列表"""
        self.steps_list.clear()
        for i, step in enumerate(self.steps):
            self.steps_list.add_step_item(step, i)

    def edit_step(self, index: int):
        """编辑步骤"""
        if 0 <= index < len(self.steps):
            step = self.steps[index]
            dialog = StepEditDialog(step.x, step.y, self, step)

            # 居中显示
            screen_geo = QApplication.primaryScreen().geometry()
            dialog.move(
                screen_geo.center().x() - dialog.width() // 2,
                screen_geo.center().y() - dialog.height() // 2
            )

            if dialog.exec() == QDialog.DialogCode.Accepted:
                self.steps[index] = dialog.get_step()
                self.update_steps_list()

    def delete_step(self, index: int):
        """删除步骤"""
        if 0 <= index < len(self.steps):
            del self.steps[index]
            self.update_steps_list()

    def update_steps_order_after_drag(self):
        """拖拽后更新步骤顺序"""
        try:
            # 获取当前列表中的步骤顺序
            new_steps = []
            for i in range(self.steps_list.count()):
                item = self.steps_list.item(i)
                widget = self.steps_list.itemWidget(item)
                if widget and hasattr(widget, 'step'):
                    new_steps.append(widget.step)

            # 更新步骤列表
            if new_steps:
                self.steps = new_steps
                self.update_steps_list()  # 重新显示以更新索引
        except Exception as e:
            print(f"Update steps order error: {e}")

    def get_feature(self) -> AutomationFeature:
        """获取编辑后的功能"""
        return AutomationFeature(
            name=self.name_edit.text(),
            steps=self.steps
        )


class MainWindow(QMainWindow):
    """主窗口类"""

    def __init__(self):
        super().__init__()
        self.window_manager = WindowManager()
        self.coordinate_capture = CoordinateCapture(self.window_manager)
        self.automation_steps = []
        self.executor = None
        self.feature_manager = FeatureManager()

        # 初始化UI组件为None
        self.window_combo = None
        self.window_info_label = None
        self.capture_button = None
        self.coordinate_label = None
        self.capture_status_label = None
        self.steps_list = None
        self.clear_steps_button = None
        self.save_feature_button = None
        self.feature_list = None

        # 添加一个标志，表示是否正在编辑
        self.is_editing = False

        # 添加按钮状态标志
        self.capture_button_is_capturing = False

        self.init_ui()
        self.setup_connections()

    def init_ui(self):
        """初始化用户界面"""
        self.setWindowTitle("自动化操作工具 v1.0")
        self.setGeometry(100, 100, 800, 600)

        # 设置样式
        self.setStyleSheet("""
            QMainWindow {
                background-color: #f0f0f0;
            }
            QTabWidget {
                border: none;
            }
            QTabWidget::pane {
                border: 1px solid #cccccc;
                border-radius: 5px;
                margin-top: -1px;
            }
            QTabWidget::tab-bar {
                alignment: left;
            }
            QTabBar::tab {
                background-color: #e0e0e0;
                border: 1px solid #cccccc;
                border-bottom-color: #cccccc;
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
                min-width: 80px;
                padding: 8px 16px;
                margin-right: 2px;
            }
            QTabBar::tab:selected {
                background-color: #ffffff;
                border-bottom-color: #ffffff;
                margin-bottom: -1px;
            }
            QTabBar::tab:hover {
                background-color: #f0f0f0;
            }
            QGroupBox {
                font-weight: bold;
                border: 2px solid #cccccc;
                border-radius: 5px;
                margin-top: 1ex;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
            }
            QPushButton {
                background-color: #4CAF50;
                border: none;
                color: white;
                padding: 8px 16px;
                text-align: center;
                font-size: 14px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton:pressed {
                background-color: #3d8b40;
            }
            QPushButton:disabled {
                background-color: #cccccc;
                color: #666666;
            }
        """)

        # 创建中央部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # 创建主布局
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(5, 5, 5, 5)

        # 创建Tab控件
        self.tab_widget = QTabWidget()
        main_layout.addWidget(self.tab_widget)

        # 创建第一个Tab：操作页面
        self.create_operation_tab()

        # 创建第二个Tab：功能管理页面
        self.create_feature_management_tab()

    def create_operation_tab(self):
        """创建操作页面Tab"""
        operation_widget = QWidget()
        operation_layout = QVBoxLayout(operation_widget)

        # 窗口绑定区域
        self.create_window_binding_section(operation_layout)

        # 坐标获取区域
        self.create_coordinate_capture_section(operation_layout)

        # 步骤管理区域
        self.create_step_management_section(operation_layout)

        self.tab_widget.addTab(operation_widget, "操作配置")

    def create_feature_management_tab(self):
        """创建功能管理页面Tab"""
        feature_widget = QWidget()
        feature_layout = QVBoxLayout(feature_widget)
        feature_layout.setContentsMargins(15, 15, 15, 15)
        feature_layout.setSpacing(15)

        # 顶部搜索和批量操作区域
        top_layout = QHBoxLayout()

        # 搜索框
        search_layout = QHBoxLayout()
        search_layout.setSpacing(0)

        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText("搜索功能...")
        self.search_box.setStyleSheet("""
            QLineEdit {
                border: 1px solid #ced4da;
                border-radius: 4px;
                padding: 8px 12px;
                font-size: 14px;
                min-width: 250px;
                background-color: white;
                color: #495057;
            }
            QLineEdit:focus {
                border: 1px solid #80bdff;
                box-shadow: 0 0 0 0.2rem rgba(0,123,255,.25);
            }
        """)
        self.search_box.textChanged.connect(self.filter_features)
        search_layout.addWidget(self.search_box)

        top_layout.addLayout(search_layout)
        top_layout.addStretch()

        # 批量操作按钮
        self.batch_select_btn = QPushButton("全选")
        self.batch_select_btn.setFixedWidth(70)
        self.batch_select_btn.setFixedHeight(36)
        self.batch_select_btn.setStyleSheet("""
            QPushButton {
                background-color: #f8f9fa;
                border: 1px solid #ced4da;
                border-radius: 4px;
                color: #212529;
                padding: 6px 12px;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: #e2e6ea;
                border-color: #dae0e5;
            }
            QPushButton:pressed {
                background-color: #dae0e5;
                border-color: #c8c9ca;
            }
        """)
        self.batch_select_btn.clicked.connect(self.toggle_select_all)
        top_layout.addWidget(self.batch_select_btn)

        self.batch_delete_btn = QPushButton("批量删除")
        self.batch_delete_btn.setFixedWidth(90)
        self.batch_delete_btn.setFixedHeight(36)
        self.batch_delete_btn.setStyleSheet("""
            QPushButton {
                background-color: #dc3545;
                border: none;
                border-radius: 4px;
                color: white;
                padding: 6px 12px;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: #c82333;
            }
            QPushButton:pressed {
                background-color: #bd2130;
            }
            QPushButton:disabled {
                background-color: #f8f9fa;
                color: #6c757d;
                border: 1px solid #ced4da;
            }
        """)
        self.batch_delete_btn.clicked.connect(self.batch_delete_features)
        self.batch_delete_btn.setEnabled(False)
        top_layout.addWidget(self.batch_delete_btn)

        self.batch_export_btn = QPushButton("批量导出")
        self.batch_export_btn.setFixedWidth(90)
        self.batch_export_btn.setFixedHeight(36)
        self.batch_export_btn.setStyleSheet("""
            QPushButton {
                background-color: #17a2b8;
                border: none;
                border-radius: 4px;
                color: white;
                padding: 6px 12px;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: #138496;
            }
            QPushButton:pressed {
                background-color: #117a8b;
            }
            QPushButton:disabled {
                background-color: #f8f9fa;
                color: #6c757d;
                border: 1px solid #ced4da;
            }
        """)
        self.batch_export_btn.clicked.connect(self.batch_export_features)
        self.batch_export_btn.setEnabled(False)
        top_layout.addWidget(self.batch_export_btn)

        feature_layout.addLayout(top_layout)

        # 功能卡片容器区域 - 添加一个带边框和背景的容器
        cards_container_widget = QWidget()
        cards_container_widget.setObjectName("cardsContainer")
        cards_container_widget.setStyleSheet("""
            QWidget#cardsContainer {
                background-color: #f8f9fa;
                border-radius: 8px;
                border: 1px solid #e9ecef;
            }
        """)
        cards_container_layout = QVBoxLayout(cards_container_widget)
        cards_container_layout.setContentsMargins(15, 15, 15, 15)
        cards_container_layout.setSpacing(0)

        # 功能卡片滚动区域
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QScrollArea.Shape.NoFrame)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll_area.setStyleSheet("""
            QScrollArea {
                border: none;
                background-color: transparent;
            }
            QScrollBar:vertical {
                border: none;
                background: #f0f0f0;
                width: 8px;
                margin: 0px;
            }
            QScrollBar::handle:vertical {
                background: #c0c0c0;
                min-height: 30px;
                border-radius: 4px;
            }
            QScrollBar::handle:vertical:hover {
                background: #a0a0a0;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
                background: none;
            }
        """)

        self.feature_cards_container = QWidget()
        self.feature_cards_layout = QVBoxLayout(self.feature_cards_container)
        self.feature_cards_layout.setContentsMargins(0, 0, 0, 0)
        self.feature_cards_layout.setSpacing(12)  # 增加卡片间距
        self.feature_cards_layout.addStretch()  # 添加弹性空间，使卡片靠上对齐

        scroll_area.setWidget(self.feature_cards_container)
        cards_container_layout.addWidget(scroll_area)

        feature_layout.addWidget(cards_container_widget)

        # 底部导入/导出按钮区域
        bottom_layout = QHBoxLayout()

        # 导入按钮
        self.import_button = QPushButton("导入功能")
        self.import_button.setFixedHeight(40)
        self.import_button.setMinimumWidth(120)
        self.import_button.setObjectName("importBtn")
        self.import_button.setStyleSheet("""
            QPushButton#importBtn {
                background-color: #17a2b8;
                border: none;
                color: white;
                font-size: 14px;
                padding: 8px 16px;
                border-radius: 6px;
            }
            QPushButton#importBtn:hover {
                background-color: #138496;
            }
            QPushButton#importBtn:pressed {
                background-color: #117a8b;
            }
        """)
        self.import_button.clicked.connect(self.import_features)
        bottom_layout.addWidget(self.import_button)

        # 导出按钮
        self.export_button = QPushButton("导出全部功能")
        self.export_button.setFixedHeight(40)
        self.export_button.setMinimumWidth(120)
        self.export_button.setObjectName("exportBtn")
        self.export_button.setStyleSheet("""
            QPushButton#exportBtn {
                background-color: #6f42c1;
                border: none;
                color: white;
                font-size: 14px;
                padding: 8px 16px;
                border-radius: 6px;
            }
            QPushButton#exportBtn:hover {
                background-color: #5a32a3;
            }
            QPushButton#exportBtn:pressed {
                background-color: #4527a0;
            }
        """)
        self.export_button.clicked.connect(self.export_features)
        bottom_layout.addWidget(self.export_button)

        bottom_layout.addStretch()

        feature_layout.addLayout(bottom_layout)

        self.tab_widget.addTab(feature_widget, "功能管理")

        # 更新功能列表显示
        self.update_feature_cards()

    def update_feature_cards(self):
        """更新功能卡片显示"""
        # 清除旧的卡片，但保留最后的弹性空间
        while self.feature_cards_layout.count() > 1:
            item = self.feature_cards_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        # 添加新卡片
        for i, feature in enumerate(self.feature_manager.features):
            card = FeatureCard(feature, i, self)
            # 在弹性空间之前插入卡片
            self.feature_cards_layout.insertWidget(self.feature_cards_layout.count() - 1, card)

    def filter_features(self):
        """根据搜索框内容过滤功能"""
        search_text = self.search_box.text().lower()

        # 遍历所有卡片，根据搜索文本显示或隐藏
        for i in range(self.feature_cards_layout.count() - 1):  # 减1是因为最后一项是弹性空间
            item = self.feature_cards_layout.itemAt(i)
            if item and item.widget():
                card = item.widget()
                if search_text in card.feature.name.lower():
                    card.setVisible(True)
                else:
                    card.setVisible(False)

    def toggle_select_all(self):
        """切换全选/取消全选"""
        # 检查当前是否有选中的卡片
        all_selected = True
        for i in range(self.feature_cards_layout.count() - 1):
            item = self.feature_cards_layout.itemAt(i)
            if item and item.widget() and item.widget().isVisible():
                card = item.widget()
                if not card.is_selected:
                    all_selected = False
                    break

        # 根据当前状态切换
        for i in range(self.feature_cards_layout.count() - 1):
            item = self.feature_cards_layout.itemAt(i)
            if item and item.widget() and item.widget().isVisible():
                card = item.widget()
                card.set_selected(not all_selected)

        # 更新按钮文本和状态
        self.batch_select_btn.setText("取消全选" if not all_selected else "全选")
        self.update_batch_buttons_state()

    def update_batch_buttons_state(self):
        """更新批量操作按钮状态"""
        # 检查是否有选中的卡片
        has_selection = False
        for i in range(self.feature_cards_layout.count() - 1):
            item = self.feature_cards_layout.itemAt(i)
            if item and item.widget():
                card = item.widget()
                if card.is_selected and card.isVisible():
                    has_selection = True
                    break

        # 更新按钮状态
        self.batch_delete_btn.setEnabled(has_selection)
        self.batch_export_btn.setEnabled(has_selection)

    def batch_delete_features(self):
        """批量删除选中的功能"""
        # 收集选中的功能索引
        selected_indices = []
        for i in range(self.feature_cards_layout.count() - 1):
            item = self.feature_cards_layout.itemAt(i)
            if item and item.widget():
                card = item.widget()
                if card.is_selected and card.isVisible():
                    selected_indices.append(card.index)

        if not selected_indices:
            return

        # 确认删除
        reply = QMessageBox.question(
            self, "确认删除", f"确定要删除选中的 {len(selected_indices)} 个功能吗？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            # 从后向前删除，避免索引变化问题
            for index in sorted(selected_indices, reverse=True):
                self.feature_manager.delete_feature(index)

            # 更新显示
            self.update_feature_cards()
            self.batch_select_btn.setText("全选")
            self.update_batch_buttons_state()

    def batch_export_features(self):
        """批量导出选中的功能"""
        # 收集选中的功能
        selected_features = []
        for i in range(self.feature_cards_layout.count() - 1):
            item = self.feature_cards_layout.itemAt(i)
            if item and item.widget():
                card = item.widget()
                if card.is_selected and card.isVisible():
                    selected_features.append(card.feature)

        if not selected_features:
            return

        # 选择保存位置
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "导出功能文件",
            "automation_features_export.json",
            "JSON文件 (*.json);;所有文件 (*)"
        )

        if file_path:
            try:
                data = [feature.to_dict() for feature in selected_features]
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)

                QMessageBox.information(self, "成功", f"成功导出 {len(selected_features)} 个功能到：\n{file_path}")
            except Exception as e:
                QMessageBox.critical(self, "导出失败", f"导出功能失败：{str(e)}")

    def run_feature(self, index: int):
        """运行指定功能"""
        if 0 <= index < len(self.feature_manager.features):
            feature = self.feature_manager.features[index]
            
            # 检查窗口是否有效
            if not self.window_manager.is_window_active():
                QMessageBox.warning(self, "警告", "绑定的窗口已失效，请重新绑定")
                return
            
            # 创建执行器
            self.executor = AutomationExecutor(feature.steps, self.window_manager)
            self.executor.step_completed.connect(self.on_step_completed)
            self.executor.execution_finished.connect(self.on_execution_finished)
            self.executor.progress_updated.connect(self.on_progress_updated)
            
            # 更新卡片状态
            for i in range(self.feature_cards_layout.count() - 1):
                item = self.feature_cards_layout.itemAt(i)
                if item and item.widget():
                    card = item.widget()
                    if card.index == index:
                        card.set_status("运行中")
                        break
            
            # 更新UI状态 - 移除对不存在的progress_bar的引用
            # self.progress_bar.setVisible(True)  # 已删除
            # self.progress_bar.setValue(0)       # 已删除
            # self.execution_status_label.setText(f"正在执行功能：{feature.name}...")  # 已删除
            
            # 开始执行
            self.executor.start()
            
            # 存储当前执行的功能索引
            self.current_running_feature_index = index

    def pause_feature(self, index: int):
        """暂停指定功能"""
        if self.executor and hasattr(self,
                                     'current_running_feature_index') and self.current_running_feature_index == index:
            if self.executor.paused:
                self.executor.resume()

                # 更新卡片状态
                for i in range(self.feature_cards_layout.count() - 1):
                    item = self.feature_cards_layout.itemAt(i)
                    if item and item.widget():
                        card = item.widget()
                        if card.index == index:
                            card.set_status("运行中")
                            card.pause_btn.setText("暂停")
                            break

                # 移除对不存在的execution_status_label的引用
                # self.execution_status_label.setText("正在执行...")
            else:
                self.executor.pause()

                # 更新卡片状态
                for i in range(self.feature_cards_layout.count() - 1):
                    item = self.feature_cards_layout.itemAt(i)
                    if item and item.widget():
                        card = item.widget()
                        if card.index == index:
                            card.set_status("暂停")
                            card.pause_btn.setText("继续")
                            break

                # 移除对不存在的execution_status_label的引用
                # self.execution_status_label.setText("已暂停")

    def create_window_binding_section(self, parent_layout):
        """创建窗口绑定区域"""
        group = QGroupBox("窗口绑定")
        layout = QGridLayout(group)

        # 窗口选择下拉框
        self.window_combo = QComboBox()
        self.window_combo.setFixedWidth(200)
        self.window_combo.currentIndexChanged.connect(self.on_window_selected)
        self.refresh_window_list()  # 初始加载窗口列表

        # 刷新按钮
        self.refresh_button = QPushButton("刷新")
        self.refresh_button.clicked.connect(self.refresh_window_list)

        # 添加到布局
        layout.addWidget(QLabel("选择窗口:"), 0, 0)
        layout.addWidget(self.window_combo, 0, 1)
        layout.addWidget(self.refresh_button, 0, 2)

        # 窗口信息显示
        self.window_info_label = QLabel("")
        self.window_info_label.setWordWrap(True)
        layout.addWidget(QLabel("窗口信息:"), 1, 0)
        layout.addWidget(self.window_info_label, 1, 1, 1, 2)

        parent_layout.addWidget(group)

    def refresh_window_list(self):
        """刷新窗口列表"""
        self.window_combo.clear()
        self.window_combo.addItem("请选择窗口", None)  # 添加默认选项

        windows = self.window_manager.get_window_list()
        for window in windows:
            self.window_combo.addItem(window['title'], window['handle'])

    def on_window_selected(self, index):
        """窗口选择变化处理"""
        if index <= 0:  # 默认选项
            self.update_binding_status(False)
            return

        window_handle = self.window_combo.currentData()
        if window_handle and self.window_manager.bind_window(window_handle):
            self.update_binding_status(True)
        else:
            self.window_combo.setCurrentIndex(0)  # 重置为默认选项
            self.update_binding_status(False)
            QMessageBox.warning(self, "错误", "绑定窗口失败")

    def update_binding_status(self, bound: bool):
        """更新绑定状态显示"""
        if bound and self.window_manager.bound_window:
            window = self.window_manager.bound_window
            rect = window['rect']
            info = f"位置: ({rect[0]}, {rect[1]})\n尺寸: {rect[2] - rect[0]} x {rect[3] - rect[1]}"
            if self.window_info_label:
                self.window_info_label.setText(info)
            if self.capture_button:
                self.capture_button.setEnabled(True)
        else:
            if self.window_info_label:
                self.window_info_label.setText("")
            if self.capture_button:
                self.capture_button.setEnabled(False)

    def create_coordinate_capture_section(self, parent_layout):
        """创建坐标获取区域"""
        group = QGroupBox("坐标获取")
        layout = QGridLayout(group)

        # 获取坐标按钮
        self.capture_button = QPushButton("获取坐标")
        self.capture_button.clicked.connect(self.toggle_coordinate_capture)
        self.capture_button.setEnabled(False)
        layout.addWidget(self.capture_button, 0, 0)

        # 坐标显示
        self.coordinate_label = QLabel("坐标: (0, 0)")
        self.coordinate_label.setStyleSheet("font-family: monospace; font-size: 14px;")
        layout.addWidget(self.coordinate_label, 0, 1)

        # 状态显示
        self.capture_status_label = QLabel("点击按钮后移动鼠标到目标位置并点击左键，按ESC取消")
        self.capture_status_label.setStyleSheet("color: #666666;")
        layout.addWidget(self.capture_status_label, 0, 2)

        parent_layout.addWidget(group)

    def create_step_management_section(self, parent_layout):
        """创建步骤管理区域"""
        group = QGroupBox("步骤管理")
        layout = QVBoxLayout(group)

        # 步骤列表
        self.steps_list = StepListWidget(self)
        layout.addWidget(self.steps_list)

        # 底部按钮区域
        button_layout = QHBoxLayout()

        # 清空列表按钮
        self.clear_steps_button = QPushButton("清空")
        self.clear_steps_button.setFixedHeight(32)
        self.clear_steps_button.setFixedWidth(60)
        self.clear_steps_button.setObjectName("clearBtn")
        self.clear_steps_button.setStyleSheet("""
            QPushButton#clearBtn {
                background-color: #f8f9fa !important;
                border: 1px solid #dee2e6 !important;
                color: #6c757d !important;
                font-size: 12px !important;
                padding: 4px 8px !important;
                border-radius: 4px !important;
            }
            QPushButton#clearBtn:hover {
                background-color: #e9ecef !important;
                color: #495057 !important;
            }
        """)
        self.clear_steps_button.clicked.connect(self.clear_steps)

        # 保存为功能按钮
        self.save_feature_button = QPushButton("保存为功能")
        self.save_feature_button.setFixedHeight(32)
        self.save_feature_button.setObjectName("saveFeatureBtn")
        self.save_feature_button.setStyleSheet("""
            QPushButton#saveFeatureBtn {
                background-color: #28a745 !important;
                border: 1px solid #20c997 !important;
                color: white !important;
                font-size: 12px !important;
                padding: 6px 12px !important;
                border-radius: 4px !important;
            }
            QPushButton#saveFeatureBtn:hover {
                background-color: #218838 !important;
            }
        """)
        self.save_feature_button.clicked.connect(self.save_as_feature)

        button_layout.addWidget(self.clear_steps_button)
        button_layout.addStretch()
        button_layout.addWidget(self.save_feature_button)

        layout.addLayout(button_layout)
        parent_layout.addWidget(group)

    def setup_connections(self):
        """设置信号连接"""
        # 步骤列表选择变化
        self.steps_list.itemSelectionChanged.connect(self.on_step_selection_changed)

        # 坐标捕获信号连接
        self.coordinate_capture.coordinate_captured.connect(self.on_coordinate_captured)
        self.coordinate_capture.capture_cancelled.connect(self.on_capture_cancelled)
        self.coordinate_capture.capture_restored.connect(self.on_capture_restored)

    def on_coordinate_captured(self, x: float, y: float):
        """坐标捕获成功处理"""
        try:
            print(f"收到坐标信号: ({x:.3f}, {y:.3f})")

            # 安全检查UI组件
            if not (self.capture_button and self.capture_status_label and self.coordinate_label):
                print("UI组件未初始化")
                return

            # 恢复按钮状态
            self.capture_button.setText("获取坐标")
            self.capture_status_label.setText("点击按钮后移动鼠标到目标位置并点击左键，按ESC取消")
            self.capture_button_is_capturing = False

            # 更新坐标显示
            self.coordinate_label.setText(f"已捕获坐标: ({x:.1%}, {y:.1%})")

            # 使用QTimer延迟显示对话框，避免在信号处理中直接创建对话框
            QTimer.singleShot(200, lambda: self._show_step_edit_dialog(x, y))

        except Exception as e:
            print(f"Coordinate captured error: {e}")
            import traceback
            traceback.print_exc()

    def _show_step_edit_dialog(self, x: float, y: float):
        """延迟显示步骤编辑对话框"""
        try:
            print(f"显示编辑对话框: ({x:.3f}, {y:.3f})")

            # 创建临时步骤
            step = AutomationStep(x=x, y=y)

            # 激活主窗口
            self.activateWindow()
            self.raise_()

            # 创建并显示编辑对话框
            dialog = StepEditDialog(x, y, self, step)

            # 居中显示
            screen_geo = QApplication.primaryScreen().geometry()
            dialog.move(
                screen_geo.center().x() - dialog.width() // 2,
                screen_geo.center().y() - dialog.height() // 2
            )

            # 显示对话框并处理结果
            if dialog.exec() == QDialog.DialogCode.Accepted:
                edited_step = dialog.get_step()
                self.automation_steps.append(edited_step)
                self.refresh_steps_list()
                print("步骤已添加到列表")
            else:
                print("用户取消了编辑")

        except Exception as e:
            print(f"Show step edit dialog error: {e}")
            import traceback
            traceback.print_exc()

    def on_capture_cancelled(self):
        """坐标捕获取消处理"""
        try:
            if self.capture_button and self.capture_status_label:
                self.capture_button.setText("获取坐标")
                self.capture_status_label.setText("已取消捕获")
                self.capture_button_is_capturing = False
        except Exception as e:
            print(f"Capture cancelled error: {e}")

    def on_capture_restored(self):
        """坐标捕获恢复处理"""
        try:
            if self.capture_button and self.capture_status_label:
                self.capture_button.setText("获取坐标")
                self.capture_status_label.setText("点击按钮后移动鼠标到目标位置并点击左键，按ESC取消")
                self.capture_button_is_capturing = False
        except Exception as e:
            print(f"Capture restored error: {e}")

    def show_window_selection(self):
        """显示窗口选择对话框"""
        windows = self.window_manager.get_window_list()
        if not windows:
            QMessageBox.warning(self, "警告", "未找到可用的窗口")
            return

        window_titles = [f"{w['title']}" for w in windows]  # 移除class名称，只显示标题
        dialog = QInputDialog(self)
        dialog.setWindowTitle("选择窗口")
        dialog.setLabelText("请选择要绑定的窗口:")
        dialog.setComboBoxItems(window_titles)
        dialog.setFixedSize(200, dialog.height())  # 设置更小的固定宽度

        # 获取对话框中的下拉框并设置其宽度
        combo_box = dialog.findChild(QComboBox)
        if combo_box:
            combo_box.setFixedWidth(200)  # 设置下拉框的固定宽度

        if dialog.exec() == QDialog.DialogCode.Accepted:
            selected_title = dialog.textValue()
            # 找到对应的窗口
            selected_window = None
            for w in windows:
                if w['title'] == selected_title:
                    selected_window = w
                    break

            if selected_window:
                if self.window_manager.bind_window(selected_window['handle']):
                    self.update_binding_status(True)
                    self.bind_button.setText("重新绑定")
                else:
                    QMessageBox.warning(self, "错误", "绑定窗口失败")

    def toggle_coordinate_capture(self):
        """切换坐标捕获状态"""
        if self.capture_button_is_capturing:
            # 停止捕获
            self.coordinate_capture.stop_capture()
            self.capture_button.setText("获取坐标")
            self.capture_status_label.setText("点击按钮后移动鼠标到目标位置并点击左键，按ESC取消")
            self.capture_button_is_capturing = False
        else:
            # 开始捕获（移除回调参数）
            if self.coordinate_capture.start_capture():
                # 开始捕获时激活目标窗口
                self.window_manager.activate_window()
                self.capture_button.setText("停止捕获")
                self.capture_status_label.setText("正在捕获坐标，请移动鼠标到目标位置并点击左键，按ESC取消")
                self.capture_button_is_capturing = True
            else:
                QMessageBox.warning(self, "错误", "请先绑定窗口")

    def show_edit_dialog(self, index: int):
        """显示编辑对话框"""
        try:
            print(f"开始显示编辑对话框，索引: {index}, 步骤数: {len(self.automation_steps)}")  # 调试信息
            if 0 <= index < len(self.automation_steps):
                step = self.automation_steps[index]

                # 创建对话框
                print("创建对话框...")  # 调试信息
                dialog = StepEditDialog(step.x, step.y, self, step)
                print("对话框创建完成")  # 调试信息

                # 确保对话框显示在屏幕中心
                screen_geo = QApplication.primaryScreen().geometry()
                dialog.move(
                    screen_geo.center().x() - dialog.width() // 2,
                    screen_geo.center().y() - dialog.height() // 2
                )

                print("显示对话框...")  # 调试信息
                # 强制显示对话框
                dialog.show()
                dialog.raise_()
                dialog.activateWindow()
                # 显示对话框
                result = dialog.exec()
                print(f"对话框结果: {result}")  # 调试信息

                if result == QDialog.DialogCode.Accepted:
                    self.automation_steps[index] = dialog.get_step()
                    self.refresh_steps_list()
                else:
                    # 如果是新添加的步骤且用户取消编辑，则删除该步骤
                    if index == len(self.automation_steps) - 1:
                        del self.automation_steps[index]
                        self.refresh_steps_list()
            else:
                print(f"无效的索引: {index}")  # 调试信息
        except Exception as e:
            print(f"Show edit dialog error: {e}")
        finally:
            # 重置编辑标志
            self.is_editing = False
            print("编辑完成，重置标志")  # 调试信息

    def refresh_steps_list(self):
        """刷新步骤列表显示"""
        try:
            if self.steps_list:
                self.steps_list.clear()
                for i, step in enumerate(self.automation_steps):
                    self.steps_list.add_step_item(step, i)
            # 更新执行按钮状态
            self.update_execution_buttons()
        except Exception as e:
            print(f"Refresh steps list error: {e}")

    def edit_step(self, index: int):
        """编辑步骤"""
        if 0 <= index < len(self.automation_steps):
            try:
                step = self.automation_steps[index]
                dialog = StepEditDialog(step.x, step.y, self, step)
                # 确保对话框显示在当前鼠标位置附近
                cursor_pos = QCursor.pos()
                dialog.move(cursor_pos.x() - dialog.width() // 2, cursor_pos.y() - dialog.height() // 2)

                if dialog.exec() == QDialog.DialogCode.Accepted:
                    self.automation_steps[index] = dialog.get_step()
                    self.refresh_steps_list()  # 使用refresh_steps_list
                else:
                    # 如果是新添加的步骤且用户取消编辑，则删除该步骤
                    if index == len(self.automation_steps) - 1 and not step.action:
                        del self.automation_steps[index]
                        self.refresh_steps_list()  # 使用refresh_steps_list
            except Exception as e:
                print(f"编辑步骤错误: {e}")

    def delete_step(self, index: int):
        """删除步骤"""
        if 0 <= index < len(self.automation_steps):
            del self.automation_steps[index]
            self.refresh_steps_list()  # 使用refresh_steps_list
            self.update_execution_buttons()

    def clear_steps(self):
        """清空步骤列表"""
        if self.automation_steps:
            reply = QMessageBox.question(
                self, "确认清空", "确定要清空所有步骤吗？",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply == QMessageBox.StandardButton.Yes:
                self.automation_steps.clear()
                self.refresh_steps_list()
                self.update_execution_buttons()

    def save_as_feature(self):
        """保存为功能"""
        if not self.automation_steps:
            QMessageBox.warning(self, "警告", "没有可保存的步骤")
            return

        # 使用简单的输入对话框
        name, ok = QInputDialog.getText(self, "保存功能", "请输入功能名称:")
        if ok and name.strip():
            feature = AutomationFeature(name.strip(), self.automation_steps.copy())
            self.feature_manager.add_feature(feature)
            self.update_feature_list()

    def update_feature_list(self):
        """更新功能列表显示（兼容旧接口）"""
        self.update_feature_cards()

    def edit_feature_by_index(self, index: int):
        """通过索引编辑功能"""
        if 0 <= index < len(self.feature_manager.features):
            feature = self.feature_manager.features[index]
            dialog = FeatureDialog(self, feature)
            if dialog.exec() == QDialog.DialogCode.Accepted:
                updated_feature = dialog.get_feature()
                self.feature_manager.update_feature(index, updated_feature)
                self.update_feature_list()

    def delete_feature_by_index(self, index: int):
        """通过索引删除功能"""
        if 0 <= index < len(self.feature_manager.features):
            feature = self.feature_manager.features[index]
            reply = QMessageBox.question(
                self, "确认删除", f"确定要删除功能 '{feature.name}' 吗？",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply == QMessageBox.StandardButton.Yes:
                self.feature_manager.delete_feature(index)
                self.update_feature_list()

    def edit_feature(self, item: QListWidgetItem):
        """编辑功能（保留双击功能）"""
        index = self.feature_list.row(item)
        self.edit_feature_by_index(index)

    def import_features(self):
        """导入功能"""
        try:
            file_path, _ = QFileDialog.getOpenFileName(
                self,
                "导入功能文件",
                "",
                "JSON文件 (*.json);;所有文件 (*)"
            )

            if file_path:
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)

                # 检查文件格式
                if isinstance(data, list):
                    imported_features = [AutomationFeature.from_dict(feature_data) for feature_data in data]

                    # 询问是否覆盖现有功能
                    if self.feature_manager.features:
                        reply = QMessageBox.question(
                            self, "导入确认",
                            f"将导入 {len(imported_features)} 个功能。\n是否覆盖现有功能？\n\n是：覆盖现有功能\n否：追加到现有功能",
                            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No | QMessageBox.StandardButton.Cancel
                        )

                        if reply == QMessageBox.StandardButton.Cancel:
                            return
                        elif reply == QMessageBox.StandardButton.Yes:
                            # 覆盖现有功能
                            self.feature_manager.features = imported_features
                        else:
                            # 追加到现有功能
                            self.feature_manager.features.extend(imported_features)
                    else:
                        # 没有现有功能，直接导入
                        self.feature_manager.features = imported_features

                    # 保存并更新显示
                    self.feature_manager.save_features()
                    self.update_feature_cards()
                    QMessageBox.information(self, "成功", f"成功导入 {len(imported_features)} 个功能")
                else:
                    QMessageBox.warning(self, "错误", "文件格式不正确")

        except Exception as e:
            QMessageBox.critical(self, "导入失败", f"导入功能失败：{str(e)}")

    def export_features(self):
        """导出功能"""
        try:
            if not self.feature_manager.features:
                QMessageBox.warning(self, "警告", "没有可导出的功能")
                # 选择保存位置
                file_path, _ = QFileDialog.getSaveFileName(
                    self,
                    "导出功能文件",
                    "automation_features_export.json",
                    "JSON文件 (*.json);;所有文件 (*)"
                )

                if file_path:
                    data = [feature.to_dict() for feature in self.feature_manager.features]
                    with open(file_path, 'w', encoding='utf-8') as f:
                        json.dump(data, f, ensure_ascii=False, indent=2)

                QMessageBox.information(self, "成功",
                                        f"成功导出 {len(self.feature_manager.features)} 个功能到：\n{file_path}")

        except Exception as e:
            QMessageBox.critical(self, "导出失败", f"导出功能失败：{str(e)}")

    def on_step_selection_changed(self):
        """步骤选择变化处理"""
        has_selection = self.steps_list.currentRow() >= 0
        # 移除对不存在的UI组件的引用
        # self.edit_step_button.setEnabled(has_selection)
        # self.delete_step_button.setEnabled(has_selection)

    def update_execution_buttons(self):
        """更新执行按钮状态"""
        has_steps = len(self.automation_steps) > 0
        # 移除对不存在的run_button的引用
        # self.run_button.setEnabled(has_steps and not self.executor)

    def on_progress_updated(self, progress: int):
        """进度更新处理"""
        # 移除对不存在的progress_bar的引用
        # if self.progress_bar:
        #     self.progress_bar.setValue(progress)
        pass

    def start_execution(self):
        """开始执行"""
        if not self.automation_steps:
            QMessageBox.warning(self, "警告", "没有可执行的步骤")
            return

        if not self.window_manager.is_window_active():
            QMessageBox.warning(self, "警告", "绑定的窗口已失效，请重新绑定")
            return
        
        # 创建执行器
        self.executor = AutomationExecutor(self.automation_steps, self.window_manager)
        self.executor.step_completed.connect(self.on_step_completed)
        self.executor.execution_finished.connect(self.on_execution_finished)
        self.executor.progress_updated.connect(self.on_progress_updated)
        
        # 更新UI状态 - 移除对不存在的UI组件的引用
        # self.run_button.setEnabled(False)
        # self.pause_button.setEnabled(True)
        # self.stop_button.setEnabled(True)
        # self.progress_bar.setVisible(True)
        # self.progress_bar.setValue(0)
        # self.execution_status_label.setText("正在执行...")
        
        # 开始执行
        self.executor.start()

    def pause_execution(self):
        """暂停执行"""
        if self.executor:
            if self.executor.paused:
                self.executor.resume()
                # 移除对不存在的UI组件的引用
                # self.pause_button.setText("暂停")
                # self.execution_status_label.setText("正在执行...")
            else:
                self.executor.pause()
                # 移除对不存在的UI组件的引用
                # self.pause_button.setText("继续")
                # self.execution_status_label.setText("已暂停")

    def stop_execution(self):
        """停止执行"""
        if self.executor:
            self.executor.stop()
            self.executor.wait()
            self.executor = None

            # 移除对不存在的UI组件的引用
            # self.run_button.setEnabled(True)
            # self.pause_button.setEnabled(False)
            # self.stop_button.setEnabled(False)
            # self.progress_bar.setVisible(False)
            # self.execution_status_label.setText("执行已停止")
            # self.update_execution_buttons()

    def on_step_completed(self, step_num: int, message: str):
        """步骤完成处理"""
        # 移除对不存在的execution_status_label的引用
        # self.execution_status_label.setText(message)
        pass

    def on_execution_finished(self, success: bool, message: str):
        """执行完成处理"""
        # 保存当前执行的功能索引
        current_index = -1
        if hasattr(self, 'current_running_feature_index'):
            current_index = self.current_running_feature_index
        
        self.executor = None
        
        # 更新UI状态 - 移除对不存在的progress_bar的引用
        # self.progress_bar.setVisible(False)
        # self.execution_status_label.setText(message)
        
        # 更新卡片状态
        if current_index >= 0:
            for i in range(self.feature_cards_layout.count() - 1):
                item = self.feature_cards_layout.itemAt(i)
                if item and item.widget():
                    card = item.widget()
                    if card.index == current_index:
                        card.set_status("错误" if not success else "停止")
                        break
        
        # 显示完成消息
        if success:
            QMessageBox.information(self, "完成", message)
        else:
            QMessageBox.warning(self, "执行失败", message)


class StepEditDialog(QDialog):
    """步骤编辑对话框"""

    def __init__(self, x: float, y: float, parent=None, step: AutomationStep = None):
        super().__init__(parent)
        self.step = step
        self.x = x
        self.y = y

        # 设置窗口标志，确保始终置顶且模态
        self.setWindowFlags(
            Qt.WindowType.Dialog |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.MSWindowsFixedSizeDialogHint
        )

        # 设置窗口属性
        self.setWindowTitle("编辑步骤")
        self.setModal(True)
        self.resize(400, 280)  # 稍微增加宽度以容纳坐标输入框

        # 初始化UI组件变量
        self.x_spinbox = None
        self.y_spinbox = None
        self.action_combo = None
        self.delay_spinbox = None
        self.text_edit = None

        # 创建UI
        self.init_ui()

    def init_ui(self):
        """初始化对话框UI"""
        # 创建主布局
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        layout.setContentsMargins(15, 15, 15, 15)

        # 坐标编辑
        coord_layout = QGridLayout()
        coord_layout.addWidget(QLabel("X坐标(%):"), 0, 0)
        self.x_spinbox = QDoubleSpinBox()
        self.x_spinbox.setRange(0.0, 100.0)
        self.x_spinbox.setSingleStep(0.1)
        self.x_spinbox.setValue(self.x * 100)  # 转换为百分比显示
        self.x_spinbox.setSuffix("%")
        coord_layout.addWidget(self.x_spinbox, 0, 1)

        coord_layout.addWidget(QLabel("Y坐标(%):"), 0, 2)
        self.y_spinbox = QDoubleSpinBox()
        self.y_spinbox.setRange(0.0, 100.0)
        self.y_spinbox.setSingleStep(0.1)
        self.y_spinbox.setValue(self.y * 100)  # 转换为百分比显示
        self.y_spinbox.setSuffix("%")
        coord_layout.addWidget(self.y_spinbox, 0, 3)

        layout.addLayout(coord_layout)

        # 动作选择
        action_layout = QHBoxLayout()
        action_layout.addWidget(QLabel("动作:"))
        self.action_combo = QComboBox()
        self.action_combo.addItems(["左键单击", "右键单击", "双击", "输入文本"])
        if self.step:
            index = self.action_combo.findText(self.step.action)
            if index >= 0:
                self.action_combo.setCurrentIndex(index)
        action_layout.addWidget(self.action_combo)
        layout.addLayout(action_layout)

        # 延迟设置
        delay_layout = QHBoxLayout()
        delay_layout.addWidget(QLabel("延迟(秒):"))
        self.delay_spinbox = QDoubleSpinBox()
        self.delay_spinbox.setRange(0.0, 10.0)
        self.delay_spinbox.setSingleStep(0.1)
        self.delay_spinbox.setValue(self.step.delay if self.step else 0.0)
        delay_layout.addWidget(self.delay_spinbox)
        layout.addLayout(delay_layout)

        # 文本输入
        text_layout = QHBoxLayout()
        text_layout.addWidget(QLabel("文本:"))
        self.text_edit = QLineEdit()
        self.text_edit.setText(self.step.text if self.step else "")
        text_layout.addWidget(self.text_edit)
        layout.addLayout(text_layout)

        # 按钮
        button_layout = QHBoxLayout()
        self.ok_button = QPushButton("确定")
        self.ok_button.clicked.connect(self.accept)
        self.cancel_button = QPushButton("取消")
        self.cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(self.ok_button)
        button_layout.addWidget(self.cancel_button)
        layout.addLayout(button_layout)

    def get_step(self) -> AutomationStep:
        """获取编辑后的步骤"""
        return AutomationStep(
            x=self.x_spinbox.value() / 100.0,  # 转换回0-1范围
            y=self.y_spinbox.value() / 100.0,  # 转换回0-1范围
            action=self.action_combo.currentText(),
            delay=self.delay_spinbox.value(),
            text=self.text_edit.text()
        )

    def closeEvent(self, event):
        """重写关闭事件，允许X按钮关闭"""
        # 允许关闭事件，相当于点击取消
        self.reject()
        event.accept()

    def keyPressEvent(self, event):
        """重写按键事件，ESC键相当于取消"""
        if event.key() == Qt.Key.Key_Escape:
            # ESC键相当于点击取消
            self.reject()
        else:
            super().keyPressEvent(event)

    def showEvent(self, event):
        """重写显示事件，确保窗口置顶"""
        super().showEvent(event)
        self.raise_()
        self.activateWindow()
        self.setFocus()


def main():
    """主函数"""
    app = QApplication(sys.argv)
    app.setApplicationName("dao")
    app.setApplicationVersion("1.0")

    # 设置应用程序图标（如果有的话）
    # app.setWindowIcon(QIcon("icon.ico"))

    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main() 
