#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
from typing import Optional
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QSplitter,
    QTreeWidget, QTreeWidgetItem, QScrollArea, QLabel, QPushButton,
    QFrame, QGroupBox, QGridLayout,
    QComboBox, QMessageBox, QSpinBox, QDoubleSpinBox
)
from PySide6.QtCore import Qt, QTimer
from typing import List, Dict, Tuple, Optional
import win32gui
import win32con
from PySide6.QtWidgets import QApplication, QLabel
from PySide6.QtCore import Qt

# 导入安全模块
try:
    import security_utils
    SECURITY_ENABLED = True
    # 开发模式：设置为False可以禁用安全检查便于调试
    DEVELOPMENT_MODE = False
except ImportError:
    SECURITY_ENABLED = False
    DEVELOPMENT_MODE = True


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




# 允许绑定的窗口标题常量
ALLOWED_WINDOW_TITLES = [
    "银数",
]

# 内置的自动化功能配置数据（新分组格式）
EMBEDDED_FEATURES_DATA = {
    "groups": [
        {
            "group_name": "默认",
            "features": [
                {
                    "name": "开",
                    "steps": [
                        {
                            "x": 0.1646,
                            "y": 0.27449999999999997,
                            "action": "左键单击",
                            "delay": 1.0,
                            "text": "",
                            "click_count": 2,
                            "click_interval": 0.05,
                            "name": ""
                        },
                        {
                            "x": 0.1641,
                            "y": 0.27940000000000004,
                            "action": "输入文本",
                            "delay": 1.0,
                            "text": "kb",
                            "click_count": 1,
                            "click_interval": 0.05,
                            "name": ""
                        },
                        {
                            "x": 0.2089,
                            "y": 0.27940000000000004,
                            "action": "左键单击",
                            "delay": 0.0,
                            "text": "",
                            "click_count": 1,
                            "click_interval": 0.05,
                            "name": ""
                        }
                    ]
                }
            ]
        },
        {
            "group_name": "测试分组",
            "features": [
                {
                    "name": "测试功能1",
                    "steps": [
                        {
                            "x": 0.5,
                            "y": 0.5,
                            "action": "左键单击",
                            "delay": 0.5,
                            "text": "",
                            "click_count": 1,
                            "click_interval": 0.05,
                            "name": "点击中心"
                        }
                    ]
                },
                {
                    "name": "测试功能2",
                    "steps": [
                        {
                            "x": 0.3,
                            "y": 0.3,
                            "action": "输入文本",
                            "delay": 0.0,
                            "text": "Hello World",
                            "click_count": 1,
                            "click_interval": 0.05,
                            "name": "输入文本"
                        }
                    ]
                }
            ]
        },
        {
            "group_name": "系统工具",
            "features": [
                {
                    "name": "系统功能",
                    "steps": [
                        {
                            "x": 0.1,
                            "y": 0.1,
                            "action": "右键单击",
                            "delay": 1.0,
                            "text": "",
                            "click_count": 1,
                            "click_interval": 0.05,
                            "name": "右键菜单"
                        }
                    ]
                }
            ]
        }
    ]
}


class FeatureGroupViewer(QMainWindow):
    """功能分组展示器 - 左侧分组导航 + 右侧功能展示"""
    
    def __init__(self):
        super().__init__()
        
        # 安全检查
        if SECURITY_ENABLED and not DEVELOPMENT_MODE:
            if not security_utils.check_security():
                QMessageBox.critical(None, "安全错误", "程序完整性验证失败")
                import sys
                sys.exit(1)
        elif SECURITY_ENABLED and DEVELOPMENT_MODE:
            # 开发模式下禁用安全保护
            security_utils.disable_security()
        
        self.features_data = []
        self.grouped_features = {}
        self.current_group = None
        self.running_features = set()
        
        # 窗口管理相关
        self.window_manager = WindowManager()
        self.window_combo: Optional[QComboBox] = None
        self.refresh_button: Optional[QPushButton] = None
        
        # 执行器相关
        self.current_executor = None
        
        # 重复执行控制
        self.current_repeat_count: int = 0
        self.target_repeat_count: int = 1
        self.repeat_interval: float = 1.0
        self.current_feature_index: int = -1
        self.repeat_timer: Optional[QTimer] = None
        
        self.init_ui()
        self.load_features()
        
    def init_ui(self):
        """初始化UI"""
        self.setWindowTitle("自动化功能管理器")
        self.setGeometry(100, 100, 900, 600)  # 减小窗口尺寸
        
        # 设置窗口图标
        from PySide6.QtGui import QIcon
        self.setWindowIcon(QIcon("C.ico"))
        
        # 设置窗口样式
        self.setStyleSheet("""
            QMainWindow {
                background-color: #f8f9fa;
            }
            QTreeWidget {
                background-color: #ffffff;
                border: 1px solid #dee2e6;
                border-radius: 6px;
                font-size: 14px;
            }
            QTreeWidget::item {
                padding: 8px;
                border-bottom: 1px solid #f1f3f4;
            }
            QTreeWidget::item:selected {
                background-color: #e3f2fd;
                color: #1976d2;
            }
            QTreeWidget::item:hover {
                background-color: #f5f5f5;
            }
            QScrollArea {
                background-color: #ffffff;
                border: 1px solid #dee2e6;
                border-radius: 6px;
            }
            QGroupBox {
                font-weight: bold;
                border: 2px solid #dee2e6;
                border-radius: 8px;
                margin-top: 10px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
            }
            QComboBox {
                padding: 5px;
                border: 1px solid #dee2e6;
                border-radius: 4px;
                background-color: white;
            }
            QComboBox:hover {
                border-color: #adb5bd;
            }
            QComboBox:focus {
                border-color: #007bff;
            }
        """)
        
        # 创建中央部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # 创建主布局
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(8, 8, 8, 8)  # 减少边距
        main_layout.setSpacing(8)  # 减少间距
        
        # 添加窗口绑定区域
        self.create_window_binding_section(main_layout)
        
        # 创建内容区域布局
        content_layout = QHBoxLayout()
        main_layout.addLayout(content_layout)
        
        # 创建分割器
        splitter = QSplitter(Qt.Horizontal)
        content_layout.addWidget(splitter)
        
        # 左侧分组导航
        self.create_group_navigation(splitter)
        
        # 右侧功能展示
        self.create_feature_display(splitter)
        
        # 设置分割器比例
        splitter.setSizes([250, 650])  # 调整左右比例
        
        # 创建状态栏
        self.create_status_bar()
        
    def create_window_binding_section(self, parent_layout):
        """创建窗口绑定区域"""
        group = QGroupBox("窗口绑定")
        group.setMaximumHeight(70)  # 限制最大高度
        layout = QHBoxLayout(group)
        layout.setContentsMargins(8, 3, 8, 3)  # 进一步减少上下边距

        # 窗口选择下拉框
        self.window_combo = QComboBox()
        self.window_combo.setFixedWidth(150)  # 减小下拉框宽度
        self.window_combo.setStyleSheet("""
            QComboBox {
                padding: 5px;
                border: 1px solid #dee2e6;
                border-radius: 4px;
                background-color: white;
            }
            QComboBox:hover {
                border-color: #adb5bd;
            }
            QComboBox:focus {
                border-color: #007bff;
            }
            QComboBox QAbstractItemView {
                border: 1px solid #dee2e6;
                selection-background-color: #e3f2fd;
                selection-color: #212529;
                background-color: white;
                padding: 5px;
            }
        """)
        self.window_combo.currentIndexChanged.connect(self.on_window_selected)
        # 延迟加载窗口列表，确保UI组件已创建
        QTimer.singleShot(100, self.refresh_window_list)

        # 刷新按钮
        self.refresh_button = QPushButton("刷新")
        self.refresh_button.clicked.connect(self.refresh_window_list)

        # 添加到布局
        layout.addWidget(QLabel("选择窗口:"))
        layout.addWidget(self.window_combo)
        layout.addWidget(self.refresh_button)
        layout.addStretch()

        parent_layout.addWidget(group)
        
    def refresh_window_list(self):
        """刷新窗口列表"""
        # 暂时断开信号连接，避免触发选择事件
        self.window_combo.currentIndexChanged.disconnect()

        self.window_combo.clear()
        self.window_combo.addItem("请选择窗口", None)  # 添加默认选项

        windows = self.window_manager.get_window_list()
        for window in windows:
            # 根据常量筛选窗口
            if self.is_window_allowed(window['title']):
                self.window_combo.addItem(window['title'], window['handle'])

        # 重新连接信号
        self.window_combo.currentIndexChanged.connect(self.on_window_selected)
        
    def is_window_allowed(self, window_title: str) -> bool:
        """检查窗口是否在允许列表中"""
        for allowed_title in ALLOWED_WINDOW_TITLES:
            if allowed_title.lower() in window_title.lower():
                return True
        return False

    def on_window_selected(self, index):
        """窗口选择变化处理"""
        if index <= 0:  # 默认选项
            return

        window_handle = self.window_combo.currentData()
        if window_handle and self.window_manager.bind_window(window_handle):
            # 设置主窗口在绑定窗口之上
            QTimer.singleShot(200, self.set_main_window_above_bound_window)
        else:
            self.window_combo.setCurrentIndex(0)  # 重置为默认选项
            QMessageBox.warning(self, "错误", "绑定窗口失败")

    def set_main_window_above_bound_window(self):
        """设置绑定窗口在主窗口之下"""
        try:
            if self.window_manager.window_handle:
                # 获取主窗口句柄
                main_hwnd = self.winId()
                if main_hwnd:
                    # 直接将绑定窗口设置在主窗口之下
                    try:
                        import win32gui
                        import win32con
                        win32gui.SetWindowPos(
                            self.window_manager.window_handle,  # 绑定窗口
                            main_hwnd,  # 主窗口句柄（作为参考窗口）
                            0, 0, 0, 0,  # 位置和大小保持不变
                            win32con.SWP_NOMOVE | win32con.SWP_NOSIZE | win32con.SWP_NOACTIVATE
                        )
                        print("绑定窗口已设置在主窗口之下")
                    except Exception as e1:
                        print(f"方法1失败: {e1}")
                        # 方法2：使用BringWindowToTop
                        try:
                            import win32gui
                            win32gui.BringWindowToTop(main_hwnd)
                            print("主窗口已置顶（方法2）")
                        except Exception as e2:
                            print(f"方法2失败: {e2}")
                            # 方法3：使用SetForegroundWindow
                            try:
                                import win32gui
                                win32gui.SetForegroundWindow(main_hwnd)
                                print("主窗口已激活（方法3）")
                            except Exception as e3:
                                print(f"方法3失败: {e3}")
                                QMessageBox.warning(
                                    self, "警告", "无法自动调整绑定窗口到当前主窗口之上，请手动操作")
        except Exception as e:
            print(f"设置窗口层级失败: {e}")
            QMessageBox.warning(self, "错误", f"设置窗口层级失败: {str(e)}")

    def update_binding_status(self, bound: bool):
        """更新绑定状态显示"""
        # 此方法已不再需要，因为移除了窗口信息显示
        pass

    def create_group_navigation(self, parent):
        """创建左侧分组导航"""
        # 分组导航容器
        group_container = QWidget()
        group_layout = QVBoxLayout(group_container)
        group_layout.setContentsMargins(0, 0, 0, 0)
        group_layout.setSpacing(5)  # 减少间距
        
        # 标题
        title_label = QLabel("📁 分组导航")
        title_label.setStyleSheet("""
            font-size: 14px; 
            font-weight: bold; 
            color: #212529; 
            padding: 8px;
            background-color: #e9ecef;
            border-radius: 6px 6px 0 0;
        """)
        group_layout.addWidget(title_label)
        
        # 分组树形控件
        self.group_tree = QTreeWidget()
        self.group_tree.setHeaderHidden(True)
        self.group_tree.setRootIsDecorated(True)
        self.group_tree.itemClicked.connect(self.on_group_selected)
        group_layout.addWidget(self.group_tree)
        
        parent.addWidget(group_container)
        
    def create_feature_display(self, parent):
        """创建右侧功能展示区域"""
        # 功能展示容器
        feature_container = QWidget()
        feature_layout = QVBoxLayout(feature_container)
        feature_layout.setContentsMargins(0, 0, 0, 0)
        
        # 标题
        self.feature_title = QLabel("📋 功能列表")
        self.feature_title.setStyleSheet("""
            font-size: 16px; 
            font-weight: bold; 
            color: #212529; 
            padding: 10px;
            background-color: #e9ecef;
            border-radius: 6px 6px 0 0;
        """)
        feature_layout.addWidget(self.feature_title)
        
        # 滚动区域
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        
        # 滚动区域内容
        self.scroll_content = QWidget()
        self.scroll_layout = QVBoxLayout(self.scroll_content)
        self.scroll_layout.setContentsMargins(10, 10, 10, 10)
        self.scroll_layout.setSpacing(15)
        self.scroll_layout.addStretch()
        
        self.scroll_area.setWidget(self.scroll_content)
        feature_layout.addWidget(self.scroll_area)
        
        parent.addWidget(feature_container)
        
    def create_status_bar(self):
        """创建状态栏"""
        self.statusBar().showMessage("就绪")
        
    def load_features(self):
        """加载功能数据"""
        try:
            # 使用内置数据（新分组格式）
            embedded_data = EMBEDDED_FEATURES_DATA.copy()
            print("✓ 使用内置配置数据")
            
            # 直接使用新格式的分组数据
            self.grouped_features = {}
            self.features_data = []  # 保持向后兼容的扁平功能列表
            
            for group_data in embedded_data['groups']:
                group_name = group_data['group_name']
                group_features = group_data['features']
                
                self.grouped_features[group_name] = group_features
                # 为向后兼容，也维护一个扁平的功能列表
                self.features_data.extend(group_features)
            
            # 更新分组导航
            self.update_group_navigation()
            
            # 默认显示第一个分组
            if self.grouped_features:
                first_group = list(self.grouped_features.keys())[0]
                self.show_group_features(first_group)
        except Exception as e:
            # 使用空数据作为备用
            self.features_data = []
            self.grouped_features = {}
            
    def update_group_navigation(self):
        """更新分组导航"""
        self.group_tree.clear()
        
        for group_name, features in self.grouped_features.items():
            # 创建分组项
            group_item = QTreeWidgetItem(self.group_tree)
            group_item.setText(0, f"🗂️ {group_name} ({len(features)})")
            group_item.setData(0, Qt.UserRole, group_name)
                
        self.group_tree.expandAll()
        
    def on_group_selected(self, item, column):
        """处理分组选择"""
        group_name = item.data(0, Qt.UserRole)
        if isinstance(group_name, str):  # 分组项
            self.show_group_features(group_name)
            
    def show_group_features(self, group_name):
        """显示指定分组的所有功能"""
        self.current_group = group_name
        self.feature_title.setText(f"📋 功能列表 - {group_name}")
        
        # 清空现有内容
        self.clear_scroll_content()
        
        # 显示该分组的所有功能
        features = self.grouped_features.get(group_name, [])
        for feature in features:
            feature_card = self.create_feature_card(feature)
            self.scroll_layout.insertWidget(0, feature_card)
            
        self.statusBar().showMessage(f"显示分组 '{group_name}' 的 {len(features)} 个功能")
        
    def show_single_feature(self, feature):
        """显示单个功能的详细信息"""
        feature_name = feature['name']
        self.statusBar().showMessage(f"显示功能 '{feature_name}' 的详细信息")
        # TODO: 实现编辑对话框
        
    def clear_scroll_content(self):
        """清空滚动区域内容"""
        while self.scroll_layout.count() > 1:  # 保留最后的stretch
            item = self.scroll_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
                
    def create_feature_card(self, feature):
        """创建功能卡片"""
        card = QFrame()
        card.setFrameStyle(QFrame.Box)
        card.setStyleSheet("""
            QFrame {
                background-color: #ffffff;
                border: 1px solid #dee2e6;
                border-radius: 8px;
                padding: 12px;
            }
            QFrame:hover {
                border-color: #adb5bd;
                box-shadow: 0 2px 8px rgba(0,0,0,0.1);
            }
        """)
        
        layout = QVBoxLayout(card)
        layout.setSpacing(8)  # 减少间距
        
        # 功能标题和基本信息
        header_layout = QHBoxLayout()
        
        # 功能名称
        name_label = QLabel(f"🎯 {feature['name']}")
        name_label.setStyleSheet("font-size: 14px; font-weight: bold; color: #212529;")
        header_layout.addWidget(name_label)
        
        header_layout.addStretch()
        layout.addLayout(header_layout)
        
        # 操作按钮
        button_layout = QHBoxLayout()
        
        # 执行参数设置
        params_layout = QVBoxLayout()
        
        # 执行次数
        repeat_layout = QHBoxLayout()
        repeat_layout.addWidget(QLabel("执行次数:"))
        repeat_count = QSpinBox()
        repeat_count.setMinimum(1)
        repeat_count.setMaximum(99999999)
        default_click_count = 1
        if feature['steps'] and len(feature['steps']) > 0:
            first_step = feature['steps'][0]
            default_click_count = first_step.get('click_count', 1)
        repeat_count.setValue(default_click_count)
        repeat_count.setFixedWidth(60)
        repeat_count.setToolTip("设置功能执行的次数")
        repeat_layout.addWidget(repeat_count)
        repeat_layout.addStretch()
        params_layout.addLayout(repeat_layout)
        
        # 执行间隔
        interval_layout = QHBoxLayout()
        interval_layout.addWidget(QLabel("间隔:"))
        repeat_interval = QDoubleSpinBox()
        repeat_interval.setMinimum(0.0)
        repeat_interval.setMaximum(99999999.0)
        # 从功能的第一步的click_interval读取默认值
        default_click_interval = 1.0
        if feature['steps'] and len(feature['steps']) > 0:
            first_step = feature['steps'][0]
            default_click_interval = first_step.get('click_interval', 1.0)
        repeat_interval.setValue(default_click_interval)
        repeat_interval.setDecimals(1)
        repeat_interval.setSuffix("s")
        repeat_interval.setFixedWidth(60)
        repeat_interval.setToolTip("设置每次执行之间的间隔时间（秒）")
        interval_layout.addWidget(repeat_interval)
        interval_layout.addStretch()
        params_layout.addLayout(interval_layout)
        
        button_layout.addLayout(params_layout)
        button_layout.addStretch()
        
        # 运行按钮
        run_btn = QPushButton("▶️ 运行")
        run_btn.setStyleSheet("""
            QPushButton {
                background-color: #28a745;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #218838;
            }
            QPushButton:pressed {
                background-color: #1e7e34;
            }
        """)
        run_btn.clicked.connect(lambda: self.run_feature(feature, repeat_count.value(), repeat_interval.value()))
        button_layout.addWidget(run_btn)
        
        # 暂停按钮
        pause_btn = QPushButton("⏸️ 暂停")
        pause_btn.setStyleSheet("""
            QPushButton {
                background-color: #ffc107;
                color: #212529;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #e0a800;
            }
        """)
        pause_btn.clicked.connect(lambda: self.pause_feature(feature))
        button_layout.addWidget(pause_btn)
        
        # 停止按钮
        stop_btn = QPushButton("⏹️ 停止")
        stop_btn.setStyleSheet("""
            QPushButton {
                background-color: #dc3545;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #c82333;
            }
        """)
        stop_btn.clicked.connect(lambda: self.stop_feature(feature))
        button_layout.addWidget(stop_btn)
        
        layout.addLayout(button_layout)
        
        return card
        
    def run_feature(self, feature, repeat_count: int = 1, repeat_interval: float = 1.0):
        """运行功能"""
        feature_name = feature['name']
        feature_index = self.features_data.index(feature)
        self.running_features.add(feature_name)
        self.statusBar().showMessage(f"正在运行功能: {feature_name}")
        
        # 检查是否有绑定的窗口
        if not self.window_manager.bound_window:
            QMessageBox.warning(self, "警告", "请先绑定目标窗口")
            return
        
        # 检查是否已有功能在运行
        if self.current_executor and self.current_executor.running:
            QMessageBox.warning(self, "警告", "已有功能正在运行，请先停止")
            return
        
        try:
            # 清理之前的执行器
            self._cleanup_executor()
            
            # 设置重复执行参数
            self.current_repeat_count = 1
            self.target_repeat_count = repeat_count
            self.repeat_interval = repeat_interval
            self.current_feature_index = feature_index
            
            # 将字典格式的步骤转换为AutomationStep对象
            from automation import AutomationStep
            automation_steps = [AutomationStep.from_dict(step) for step in feature['steps']]
            
            # 创建新的执行器
            from automation import AutomationExecutor
            self.current_executor = AutomationExecutor(automation_steps, self.window_manager, feature_index)
            
            # 连接信号
            self.current_executor.execution_finished.connect(self._on_execution_finished)
            
            # 最小化主窗口
            self.showMinimized()
            
            # 激活目标窗口
            self.window_manager.activate_window()
            import time
            time.sleep(1.0)  # 等待窗口激活
            
            # 启动执行器
            self.current_executor.start()
            
        except Exception as e:
            QMessageBox.critical(self, "错误", f"启动功能执行失败: {str(e)}")
            # 恢复主窗口
            self.showNormal()
            self._reset_repeat_state()
    
    def _on_execution_finished(self, success: bool, message: str):
        """执行完成处理"""
        print(f"[EXECUTION] 第 {self.current_repeat_count}/{self.target_repeat_count} 次执行完成: {success}")
        
        # 清理当前执行器
        self._cleanup_executor()
        
        if success and self.current_repeat_count < self.target_repeat_count:
            # 需要执行下一次
            self.current_repeat_count += 1
            
            if self.repeat_interval <= 0:
                # 无间隔，立即执行下一次
                print("[EXECUTION] 无间隔，立即开始下一次")
                QTimer.singleShot(0, self._execute_next_unit)
            else:
                # 有间隔，延迟执行
                print(f"[EXECUTION] 等待 {self.repeat_interval} 秒后执行下一次")
                if not self.repeat_timer:
                    self.repeat_timer = QTimer()
                    self.repeat_timer.setSingleShot(True)
                    self.repeat_timer.timeout.connect(self._execute_next_unit)
                
                interval_ms = int(self.repeat_interval * 1000)
                self.repeat_timer.start(interval_ms)
        else:
            # 所有执行完成或失败
            if success:
                final_message = f"所有执行完成，共 {self.current_repeat_count} 次"
            else:
                final_message = f"执行中断: {message} (已完成 {self.current_repeat_count-1} 次)"
            
            print(f"[EXECUTION] 最终结果: {final_message}")
            self.on_execution_finished(success, final_message)
            
            # 重置状态
            self._reset_repeat_state()
    
    def _execute_next_unit(self):
        """执行下一个最小单元"""
        if self.current_feature_index >= 0:
            feature = self.features_data[self.current_feature_index]
            self._execute_minimal_unit(feature)
    
    def _execute_minimal_unit(self, feature):
        """执行一个最小单元（一次完整功能）"""
        try:
            print(f"[MINIMAL_UNIT] 开始第 {self.current_repeat_count}/{self.target_repeat_count} 次执行")
            
            # 将字典格式的步骤转换为AutomationStep对象
            from automation import AutomationStep
            automation_steps = [AutomationStep.from_dict(step) for step in feature['steps']]
            
            # 创建新的执行器
            from automation import AutomationExecutor
            self.current_executor = AutomationExecutor(automation_steps, self.window_manager, self.current_feature_index)
            
            # 连接信号
            self.current_executor.execution_finished.connect(self._on_execution_finished)
            
            # 激活目标窗口
            self.window_manager.activate_window()
            import time
            time.sleep(1.0)  # 等待窗口激活
            
            # 启动执行器
            self.current_executor.start()
            
        except Exception as e:
            print(f"[MINIMAL_UNIT] 启动最小单元失败: {e}")
            import traceback
            traceback.print_exc()
            self._reset_repeat_state()
    
    def on_execution_finished(self, success: bool, message: str):
        """执行完成回调"""
        try:
            print(f"[SIGNAL] 执行完成回调: 成功: {success}, 消息: {message}")
            # 恢复主窗口
            self.showNormal()
            
            if success:
                QMessageBox.information(self, "执行完成", f"功能执行完成: {message}")
            else:
                QMessageBox.warning(self, "执行失败", f"功能执行失败: {message}")
        except Exception as e:
            print(f"[SIGNAL] 执行完成回调错误: {e}")
            import traceback
            traceback.print_exc()
            # 确保主窗口恢复
            try:
                self.showNormal()
            except BaseException:
                pass
    
    def _reset_repeat_state(self):
        """重置重复执行状态"""
        self.current_repeat_count = 0
        self.target_repeat_count = 1
        self.repeat_interval = 1.0
        self.current_feature_index = -1
        if self.repeat_timer:
            self.repeat_timer.stop()
            self.repeat_timer.deleteLater()
            self.repeat_timer = None
        self._cleanup_executor()
        
    def _cleanup_executor(self):
        """清理当前执行器"""
        if hasattr(self, 'current_executor') and self.current_executor:
            try:
                if self.current_executor.isRunning():
                    self.current_executor.stop()
                    self.current_executor.wait(3000)  # 等待最多3秒
                self.current_executor.deleteLater()
            except Exception as e:
                print(f"清理执行器失败: {e}")
            finally:
                self.current_executor = None
        
    def pause_feature(self, feature):
        """暂停功能"""
        feature_name = feature['name']
        feature_index = self.features_data.index(feature)
        
        # 如果是当前运行的功能，直接控制
        if hasattr(self, 'current_executor') and self.current_executor:
            if self.current_executor.running:
                if hasattr(self.current_executor, 'paused') and self.current_executor.paused:
                    # 恢复执行
                    self.current_executor.resume()
                    self.statusBar().showMessage(f"恢复功能: {feature_name}")
                else:
                    # 暂停执行
                    self.current_executor.pause()
                    self.statusBar().showMessage(f"暂停功能: {feature_name}")
        
    def stop_feature(self, feature):
        """停止功能"""
        feature_name = feature['name']
        if feature_name in self.running_features:
            self.running_features.remove(feature_name)
        
        # 停止执行器
        if hasattr(self, 'current_executor') and self.current_executor:
            self.current_executor.stop()
            self._cleanup_executor()
            
        self.statusBar().showMessage(f"停止功能: {feature_name}")
        # 恢复主窗口
        self.showNormal()
        
    def edit_feature(self, feature):
        """编辑功能"""
        feature_name = feature['name']
        self.statusBar().showMessage(f"编辑功能: {feature_name}")
        # 此功能已移除
        
    def delete_feature(self, feature):
        """删除功能"""
        feature_name = feature['name']
        self.statusBar().showMessage(f"删除功能: {feature_name}")
        # 此功能已移除


if __name__ == "__main__":
    import sys
    from PySide6.QtWidgets import QApplication
    
    app = QApplication(sys.argv)
    
    # 设置应用程序样式
    app.setStyle('Fusion')
    
    viewer = FeatureGroupViewer()
    viewer.show()
    
    sys.exit(app.exec()) 