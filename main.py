#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import time
import json
import os
from typing import List, Dict, Optional, Tuple
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                               QHBoxLayout, QGridLayout, QLabel, QPushButton,
                               QListWidget, QListWidgetItem, QComboBox, QSpinBox,
                               QTextEdit, QGroupBox, QMessageBox, QInputDialog,
                               QProgressBar, QCheckBox, QLineEdit, QFrame, QDialog, QDoubleSpinBox)
from PySide6.QtCore import Qt, QThread, Signal, QTimer, QPoint
from PySide6.QtGui import QFont, QIcon, QPalette, QColor
import win32gui
import win32api
import win32con
from pynput import mouse, keyboard
from pynput.mouse import Button, Listener as MouseListener
from pynput.keyboard import Key, Listener as KeyboardListener
from PySide6.QtGui import QCursor # Added missing import


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

class CoordinateCapture:
    """坐标捕获器"""
    def __init__(self, window_manager: WindowManager):
        self.window_manager = window_manager  # 修复：使用传入的window_manager而不是创建新的
        self.capturing = False
        self.mouse_listener = None
        self.keyboard_listener = None
        self.captured_coordinates = []
        self.on_capture_callback = None
        self.floating_label = None
        self.last_coordinates = None
        self._current_pos = None
        self._update_timer = QTimer()
        self._update_timer.setInterval(33)
        self._update_timer.timeout.connect(self._update_label)

    def start_capture(self, callback=None):
        """开始坐标捕获"""
        if not self.window_manager.bound_window:
            return False
        
        self.capturing = True
        self.on_capture_callback = callback
        
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
            
            # 通知UI更新状态
            if self.on_capture_callback:
                self.on_capture_callback("restore")
        except Exception as e:
            print(f"Stop capture error: {e}")

    def _on_click(self, x, y, button, pressed):
        """鼠标点击事件处理"""
        if pressed and button == Button.left and self.capturing:
            try:
                # 停止定时器
                if self._update_timer.isActive():
                    self._update_timer.stop()
                
                # 获取相对坐标
                rel_x, rel_y = self.window_manager.get_relative_coordinates(x, y)
                self.captured_coordinates.append((rel_x, rel_y))
                
                # 隐藏悬浮窗
                if self.floating_label and self.floating_label.isVisible():
                    self.floating_label.hide()
                
                # 停止监听器
                self.capturing = False
                if self.mouse_listener:
                    self.mouse_listener.stop()
                    self.mouse_listener = None
                if self.keyboard_listener:
                    self.keyboard_listener.stop()
                    self.keyboard_listener = None
                
                # 通知UI更新
                if self.on_capture_callback:
                    # 使用QTimer确保在主线程中调用回调
                    QTimer.singleShot(0, lambda: self.on_capture_callback("captured", (rel_x, rel_y)))
                
                return False
            except Exception as e:
                print(f"Click handling error: {e}")
                self.stop_capture()
                return False
    
    def _on_key_press(self, key):
        """键盘按键事件处理"""
        if key == Key.esc and self.capturing:
            try:
                self.stop_capture()
                if self.floating_label:
                    self.floating_label.hide()
                if self.on_capture_callback:
                    self.on_capture_callback("cancelled")
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
        edit_btn = QPushButton("✎")
        edit_btn.setFixedSize(24, 24)
        edit_btn.setStyleSheet("""
            QPushButton {
                border: none;
                background: transparent;
                color: #666;
            }
            QPushButton:hover {
                color: #000;
            }
        """)
        edit_btn.clicked.connect(lambda: self.parent.edit_step(self.index))
        layout.addWidget(edit_btn)

        # 删除按钮
        delete_btn = QPushButton("−")
        delete_btn.setFixedSize(24, 24)
        delete_btn.setStyleSheet("""
            QPushButton {
                border: none;
                background: transparent;
                color: #666;
            }
            QPushButton:hover {
                color: #f00;
            }
        """)
        delete_btn.clicked.connect(lambda: self.parent.delete_step(self.index))
        layout.addWidget(delete_btn)

class FeatureDialog(QDialog):
    """功能编辑对话框"""
    def __init__(self, parent=None, feature: AutomationFeature = None):
        super().__init__(parent)
        self.feature = feature
        self.steps = feature.steps if feature else []
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("编辑功能")
        self.setModal(True)
        self.resize(500, 400)

        layout = QVBoxLayout(self)

        # 功能名称
        name_layout = QHBoxLayout()
        name_layout.addWidget(QLabel("功能名称:"))
        self.name_edit = QLineEdit()
        if self.feature:
            self.name_edit.setText(self.feature.name)
        name_layout.addWidget(self.name_edit)
        layout.addLayout(name_layout)

        # 步骤列表
        self.steps_list = StepListWidget(self)
        self.update_steps_list()
        layout.addWidget(self.steps_list)

        # 按钮
        button_layout = QHBoxLayout()
        self.ok_button = QPushButton("确定")
        self.ok_button.clicked.connect(self.accept)
        self.cancel_button = QPushButton("取消")
        self.cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(self.ok_button)
        button_layout.addWidget(self.cancel_button)
        layout.addLayout(button_layout)

    def update_steps_list(self):
        """更新步骤列表"""
        self.steps_list.clear()
        for i, step in enumerate(self.steps):
            self.steps_list.add_step_item(step, i)

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
        
        # 窗口绑定区域
        self.create_window_binding_section(main_layout)
        
        # 坐标获取区域
        self.create_coordinate_capture_section(main_layout)
        
        # 步骤管理区域
        self.create_step_management_section(main_layout)
        
        # 执行控制区域
        self.create_execution_control_section(main_layout)
    
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
            info = f"位置: ({rect[0]}, {rect[1]})\n尺寸: {rect[2]-rect[0]} x {rect[3]-rect[1]}"
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
        
        # 清空列表按钮（小按钮）
        self.clear_steps_button = QPushButton("清空")
        self.clear_steps_button.setFixedSize(60, 24)
        self.clear_steps_button.clicked.connect(self.clear_steps)
        
        # 保存为功能按钮
        self.save_feature_button = QPushButton("保存为功能")
        self.save_feature_button.clicked.connect(self.save_as_feature)
        
        button_layout.addWidget(self.clear_steps_button)
        button_layout.addStretch()
        button_layout.addWidget(self.save_feature_button)
        
        layout.addLayout(button_layout)
        parent_layout.addWidget(group)
        
        # 创建功能列表区域
        self.create_feature_list_section(parent_layout)
    
    def create_feature_list_section(self, parent_layout):
        """创建功能列表区域"""
        group = QGroupBox("功能列表")
        layout = QVBoxLayout(group)
        
        # 功能列表
        self.feature_list = QListWidget()
        self.feature_list.itemDoubleClicked.connect(self.edit_feature)
        layout.addWidget(self.feature_list)
        
        # 更新功能列表显示
        self.update_feature_list()
        
        parent_layout.addWidget(group)
    
    def create_execution_control_section(self, parent_layout):
        """创建执行控制区域"""
        group = QGroupBox("执行控制")
        layout = QVBoxLayout(group)
        
        # 执行按钮
        button_layout = QHBoxLayout()
        
        self.run_button = QPushButton("开始执行")
        self.run_button.clicked.connect(self.start_execution)
        self.run_button.setEnabled(False)
        button_layout.addWidget(self.run_button)
        
        self.pause_button = QPushButton("暂停")
        self.pause_button.clicked.connect(self.pause_execution)
        self.pause_button.setEnabled(False)
        button_layout.addWidget(self.pause_button)
        
        self.stop_button = QPushButton("停止")
        self.stop_button.clicked.connect(self.stop_execution)
        self.stop_button.setEnabled(False)
        button_layout.addWidget(self.stop_button)
        
        layout.addLayout(button_layout)
        
        # 进度条
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)
        
        # 执行状态
        self.execution_status_label = QLabel("")
        layout.addWidget(self.execution_status_label)
        
        parent_layout.addWidget(group)
    
    def setup_connections(self):
        """设置信号连接"""
        # 步骤列表选择变化
        self.steps_list.itemSelectionChanged.connect(self.on_step_selection_changed)
    
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
        if self.coordinate_capture.capturing:
            self.coordinate_capture.stop_capture()
            self.capture_button.setText("获取坐标")
            self.capture_status_label.setText("点击按钮后移动鼠标到目标位置并点击左键，按ESC取消")
        else:
            if self.coordinate_capture.start_capture(self.handle_capture_event):
                # 开始捕获时激活目标窗口
                self.window_manager.activate_window()
                self.capture_button.setText("停止捕获")
                self.capture_status_label.setText("正在捕获坐标，请移动鼠标到目标位置并点击左键，按ESC取消")
            else:
                QMessageBox.warning(self, "错误", "请先绑定窗口")

    def handle_capture_event(self, event_type, data=None):
        """处理捕获事件"""
        try:
            print(f"处理捕获事件: {event_type}")  # 调试信息
            if event_type == "captured" and not self.is_editing:
                self.capture_button.setText("获取坐标")
                x, y = data
                self.coordinate_label.setText(f"已捕获坐标: ({x:.1%}, {y:.1%})")
                print(f"捕获的坐标: ({x:.1%}, {y:.1%})")  # 调试信息
                
                # 立即添加到步骤列表
                step = AutomationStep(x=x, y=y)
                self.automation_steps.append(step)
                self.refresh_steps_list()
                
                # 设置编辑标志
                self.is_editing = True
                
                # 使用独立函数显示对话框，避免闭包问题
                QTimer.singleShot(100, lambda: self._show_dialog_for_index(len(self.automation_steps) - 1))
            
            elif event_type == "cancelled":
                self.capture_button.setText("获取坐标")
                self.capture_status_label.setText("已取消捕获")
        except Exception as e:
            print(f"Handle capture event error: {e}")
            self.is_editing = False

    def _show_dialog_for_index(self, index):
        """显示特定索引的编辑对话框"""
        try:
            print(f"显示编辑对话框，索引: {index}")  # 调试信息
            self.show_edit_dialog(index)
        except Exception as e:
            print(f"Show dialog error: {e}")
            self.is_editing = False

    def show_edit_dialog(self, index: int):
        """显示编辑对话框"""
        try:
            print(f"开始显示编辑对话框，索引: {index}, 步骤数: {len(self.automation_steps)}")  # 调试信息
            if 0 <= index < len(self.automation_steps):
                step = self.automation_steps[index]
                
                # 创建并配置对话框
                dialog = StepEditDialog(step.x, step.y, self, step)
                dialog.setWindowFlags(
                    Qt.WindowType.Window | 
                    Qt.WindowType.WindowStaysOnTopHint |
                    Qt.WindowType.WindowModal
                )
                
                # 确保对话框显示在屏幕中心
                screen_geo = QApplication.primaryScreen().geometry()
                dialog.move(
                    screen_geo.center().x() - dialog.width() // 2,
                    screen_geo.center().y() - dialog.height() // 2
                )
                
                print("显示对话框...")  # 调试信息
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
        
        dialog = FeatureDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            feature = dialog.get_feature()
            self.feature_manager.add_feature(feature)
            self.update_feature_list()
    
    def update_feature_list(self):
        """更新功能列表显示"""
        self.feature_list.clear()
        for feature in self.feature_manager.features:
            item = QListWidgetItem(feature.name)
            self.feature_list.addItem(item)
    
    def edit_feature(self, item: QListWidgetItem):
        """编辑功能"""
        index = self.feature_list.row(item)
        feature = self.feature_manager.features[index]
        dialog = FeatureDialog(self, feature)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            updated_feature = dialog.get_feature()
            self.feature_manager.update_feature(index, updated_feature)
            self.update_feature_list()
    
    def on_step_selection_changed(self):
        """步骤选择变化处理"""
        has_selection = self.steps_list.currentRow() >= 0
        self.edit_step_button.setEnabled(has_selection)
        self.delete_step_button.setEnabled(has_selection)
    
    def update_execution_buttons(self):
        """更新执行按钮状态"""
        has_steps = len(self.automation_steps) > 0
        self.run_button.setEnabled(has_steps and not self.executor)
    
    def on_progress_updated(self, progress: int):
        """进度更新处理"""
        if self.progress_bar:
            self.progress_bar.setValue(progress)
    
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
        
        # 更新UI状态
        self.run_button.setEnabled(False)
        self.pause_button.setEnabled(True)
        self.stop_button.setEnabled(True)
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.execution_status_label.setText("正在执行...")
        
        # 开始执行
        self.executor.start()
    
    def pause_execution(self):
        """暂停执行"""
        if self.executor:
            if self.executor.paused:
                self.executor.resume()
                self.pause_button.setText("暂停")
                self.execution_status_label.setText("正在执行...")
            else:
                self.executor.pause()
                self.pause_button.setText("继续")
                self.execution_status_label.setText("已暂停")
    
    def stop_execution(self):
        """停止执行"""
        if self.executor:
            self.executor.stop()
            self.executor.wait()
            self.executor = None
            
            # 更新UI状态
            self.run_button.setEnabled(True)
            self.pause_button.setEnabled(False)
            self.stop_button.setEnabled(False)
            self.progress_bar.setVisible(False)
            self.execution_status_label.setText("执行已停止")
            self.update_execution_buttons()
    
    def on_step_completed(self, step_num: int, message: str):
        """步骤完成处理"""
        self.execution_status_label.setText(message)
    
    def on_execution_finished(self, success: bool, message: str):
        """执行完成处理"""
        self.executor = None
        
        # 更新UI状态
        self.run_button.setEnabled(True)
        self.pause_button.setEnabled(False)
        self.stop_button.setEnabled(False)
        self.progress_bar.setVisible(False)
        self.execution_status_label.setText(message)
        self.update_execution_buttons()
        
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
        # 设置窗口标志，确保显示在最上层
        self.setWindowFlags(
            Qt.WindowType.Window |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.WindowModal
        )
        self.init_ui(x, y)
        
        # 确保对话框显示在前台
        self.setFocus()
        self.activateWindow()
        self.raise_()
    
    def init_ui(self, x: float, y: float):
        """初始化对话框UI"""
        self.setWindowTitle("编辑步骤")
        self.setModal(True)
        self.setFixedSize(300, 200)  # 设置固定大小
        
        layout = QVBoxLayout(self)
        layout.setSpacing(10)  # 设置控件间距
        
        # 坐标显示（只读）
        coord_layout = QHBoxLayout()
        coord_layout.addWidget(QLabel(f"X坐标: {x:.1%}"))
        coord_layout.addWidget(QLabel(f"Y坐标: {y:.1%}"))
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
            x=self.x,  # 使用保存的坐标值
            y=self.y,
            action=self.action_combo.currentText(),
            delay=self.delay_spinbox.value(),
            text=self.text_edit.text()
        )
    
    # 重写显示事件，确保对话框显示
    def showEvent(self, event):
        super().showEvent(event)
        self.activateWindow()
        self.raise_()
        print("对话框显示事件触发")  # 调试信息


def main():
    """主函数"""
    app = QApplication(sys.argv)
    app.setApplicationName("自动化操作工具")
    app.setApplicationVersion("1.0")
    
    # 设置应用程序图标（如果有的话）
    # app.setWindowIcon(QIcon("icon.ico"))
    
    window = MainWindow()
    window.show()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main() 
