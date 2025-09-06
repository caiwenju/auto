#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import time
import json
from typing import Optional
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QGridLayout, QLabel, QPushButton, QListWidget,
    QComboBox, QGroupBox, QMessageBox, QLineEdit,
    QDialog, QFileDialog, QTabWidget, QScrollArea, QSystemTrayIcon,
    QSplitter, QTreeWidget, QTreeWidgetItem, QFrame, QMenu
)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QCursor, QIcon
import win32gui
import win32con

# 导入自定义模块
from window_manager import WindowManager
from coordinate_capture import CoordinateCapture
from automation import AutomationStep, AutomationFeature, FeatureGroup, FeatureManager, AutomationExecutor
from ui_components import StepListWidget, FeatureCardWidget, GroupCard
from dialogs import FeatureDialog, StepEditDialog, GroupDialog


class MainWindow(QMainWindow):
    """主窗口类"""

    def __init__(self):
        super().__init__()
        self.window_manager = WindowManager()
        self.coordinate_capture = CoordinateCapture(self.window_manager)
        self.automation_steps = []
        self.feature_manager = FeatureManager()

        # 初始化UI组件为None
        self.window_combo: Optional[QComboBox] = None
        self.window_info_label: Optional[QLabel] = None
        self.capture_button: Optional[QPushButton] = None
        self.coordinate_label: Optional[QLabel] = None
        self.capture_status_label: Optional[QLabel] = None
        self.steps_list: Optional[StepListWidget] = None
        self.clear_steps_button: Optional[QPushButton] = None
        self.save_feature_button: Optional[QPushButton] = None
        self.feature_list: Optional[QListWidget] = None

        # 窗口绑定相关组件
        self.refresh_button: Optional[QPushButton] = None

        # 功能管理相关组件
        self.search_box: Optional[QLineEdit] = None
        self.batch_select_btn: Optional[QPushButton] = None
        self.batch_delete_btn: Optional[QPushButton] = None
        self.batch_export_btn: Optional[QPushButton] = None
        self.feature_cards_container: Optional[QWidget] = None
        self.feature_cards_layout: Optional[QVBoxLayout] = None
        self.import_button: Optional[QPushButton] = None
        self.export_button: Optional[QPushButton] = None
        
        # 左右分栏相关组件
        self.group_tree: Optional[QTreeWidget] = None
        self.add_group_button: Optional[QPushButton] = None
        self.feature_title: Optional[QLabel] = None
        self.scroll_area: Optional[QScrollArea] = None
        self.scroll_content: Optional[QWidget] = None
        self.scroll_layout: Optional[QVBoxLayout] = None
        self.current_group: Optional[str] = None
        
        # 全局选择状态管理（支持多分组勾选）
        self.global_selected_features: set = set()

        # 添加一个标志，表示是否正在编辑
        self.is_editing: bool = False

        # 添加按钮状态标志
        self.capture_button_is_capturing: bool = False

        # 添加托盘图标
        self.tray_icon: Optional[QSystemTrayIcon] = None
        self.tray_notification_shown: bool = False  # 标记是否已显示过托盘提示
        self.setup_tray_icon()

        # 窗口层级监控相关
        self.zorder_monitor_timer: Optional[QTimer] = None
        self.is_monitoring_zorder: bool = False

        # 最小单元重复执行控制
        self.current_repeat_count: int = 0
        self.target_repeat_count: int = 1
        self.repeat_interval: float = 1.0
        self.current_feature_index: int = -1
        self.repeat_timer: Optional[QTimer] = None
        self.current_executor: Optional[AutomationExecutor] = None

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
        feature_layout.setContentsMargins(8, 8, 8, 8)
        feature_layout.setSpacing(8)

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

        # 创建内容区域布局（左右分栏）
        content_layout = QHBoxLayout()
        feature_layout.addLayout(content_layout)
        
        # 创建分割器
        from PySide6.QtWidgets import QSplitter
        splitter = QSplitter(Qt.Horizontal)
        content_layout.addWidget(splitter)
        
        # 左侧分组导航
        self.create_group_navigation(splitter)
        
        # 右侧功能展示
        self.create_feature_display(splitter)
        
        # 设置分割器比例
        splitter.setSizes([250, 550])

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

    def create_group_navigation(self, parent):
        """创建左侧分组导航"""
        # 分组导航容器
        group_container = QWidget()
        group_layout = QVBoxLayout(group_container)
        group_layout.setContentsMargins(0, 0, 0, 0)
        group_layout.setSpacing(5)
        
        # 标题栏（包含标题和新增按钮）
        title_container = QWidget()
        title_container.setStyleSheet("""
            background-color: #e9ecef;
            border-radius: 6px 6px 0 0;
        """)
        title_layout = QHBoxLayout(title_container)
        title_layout.setContentsMargins(8, 8, 8, 8)
        title_layout.setSpacing(5)
        
        title_label = QLabel("📁 分组导航")
        title_label.setStyleSheet("""
            font-size: 14px; 
            font-weight: bold; 
            color: #212529; 
            background-color: transparent;
        """)
        title_layout.addWidget(title_label)
        title_layout.addStretch()
        
        # 新增分组按钮
        self.add_group_button = QPushButton("＋")
        self.add_group_button.setFixedSize(28, 28)  # 稍微增大
        self.add_group_button.setObjectName("addGroupBtn")
        self.add_group_button.setStyleSheet("""
            QPushButton#addGroupBtn {
                background-color: #28a745;
                border: none;
                color: white;
                font-size: 18px;
                font-weight: bold;
                border-radius: 14px;
                padding: 0px;
            }
            QPushButton#addGroupBtn:hover {
                background-color: #218838;
            }
            QPushButton#addGroupBtn:pressed {
                background-color: #1e7e34;
            }
        """)
        self.add_group_button.setToolTip("新增分组")
        self.add_group_button.clicked.connect(self.add_new_group)
        title_layout.addWidget(self.add_group_button)
        
        group_layout.addWidget(title_container)
        
        # 分组树形控件
        self.group_tree = QTreeWidget()
        self.group_tree.setHeaderHidden(True)
        self.group_tree.setRootIsDecorated(True)
        self.group_tree.setStyleSheet("""
            QTreeWidget {
                background-color: #ffffff;
                border: 1px solid #dee2e6;
                border-radius: 6px;
                font-size: 14px;
            }
            QTreeWidget::item {
                padding: 0px;
                border-bottom: 1px solid #f1f3f4;
                min-height: 40px;
            }
            QTreeWidget::item:selected {
                background-color: #e3f2fd;
                color: #1976d2;
            }
            QTreeWidget::item:hover {
                background-color: transparent;
            }
        """)
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
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.scroll_area.setStyleSheet("""
            QScrollArea {
                background-color: #ffffff;
                border: 1px solid #dee2e6;
                border-radius: 6px;
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
        
        # 滚动区域内容
        self.scroll_content = QWidget()
        self.scroll_layout = QVBoxLayout(self.scroll_content)
        self.scroll_layout.setContentsMargins(10, 10, 10, 10)
        self.scroll_layout.setSpacing(15)
        self.scroll_layout.addStretch()
        
        self.scroll_area.setWidget(self.scroll_content)
        feature_layout.addWidget(self.scroll_area)
        
        parent.addWidget(feature_container)

    def update_feature_cards(self):
        """更新功能卡片显示（使用左右分栏布局）"""
        # 更新左侧分组导航
        self.update_group_navigation()
        
        # 如果有当前选中的分组，显示该分组的功能
        if self.current_group:
            self.show_group_features(self.current_group)
        else:
            # 默认显示第一个分组
            all_groups = self.feature_manager.get_all_groups()
            if all_groups:
                first_group = all_groups[0]
                self.show_group_features(first_group)

    def update_group_navigation(self):
        """更新分组导航"""
        if not self.group_tree:
            return
            
        self.group_tree.clear()
        
        # 创建分组项
        for group in self.feature_manager.groups:
            group_item = QTreeWidgetItem(self.group_tree)
            group_item.setData(0, Qt.UserRole, group.group_name)
            
            # 创建自定义widget包含分组名称和编辑按钮
            group_widget = self.create_group_item_widget(group.group_name, group.get_feature_count())
            self.group_tree.setItemWidget(group_item, 0, group_widget)
                
        self.group_tree.expandAll()

    def create_group_item_widget(self, group_name: str, feature_count: int):
        """创建分组项的自定义widget"""
        widget = QWidget()
        widget.setMinimumHeight(40)  # 设置最小高度
        widget.setStyleSheet("""
            QWidget {
                background-color: transparent;
            }
            QWidget:hover {
                background-color: #f8f9fa;
                border-radius: 4px;
            }
        """)
        
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(8, 6, 8, 6)  # 增加内边距
        layout.setSpacing(8)
        
        # 分组名称和数量标签
        group_label = QLabel(f"🗂️ {group_name} ({feature_count})")
        group_label.setStyleSheet("""
            QLabel {
                color: #212529;
                font-size: 15px;
                font-weight: 500;
                padding: 6px 8px;
                background-color: transparent;
            }
        """)
        layout.addWidget(group_label)
        
        layout.addStretch()
        
        # 编辑按钮
        edit_button = QPushButton("✏️")
        edit_button.setFixedSize(24, 24)  # 增大按钮尺寸
        edit_button.setStyleSheet("""
            QPushButton {
                background-color: #f8f9fa;
                border: 1px solid #dee2e6;
                border-radius: 12px;
                font-size: 13px;
                padding: 0px;
            }
            QPushButton:hover {
                background-color: #e9ecef;
                border-color: #adb5bd;
            }
            QPushButton:pressed {
                background-color: #dee2e6;
            }
        """)
        edit_button.setToolTip("编辑分组名称")
        edit_button.clicked.connect(lambda: self.edit_group_name(group_name))
        layout.addWidget(edit_button)
        
        # 删除按钮
        delete_button = QPushButton("🗑️")
        delete_button.setFixedSize(24, 24)  # 增大按钮尺寸
        delete_button.setStyleSheet("""
            QPushButton {
                background-color: #f8f9fa;
                border: 1px solid #dee2e6;
                border-radius: 12px;
                font-size: 13px;
                padding: 0px;
            }
            QPushButton:hover {
                background-color: #f5c6cb;
                border-color: #f1aeb5;
            }
            QPushButton:pressed {
                background-color: #f1aeb5;
            }
        """)
        delete_button.setToolTip("删除分组")
        delete_button.clicked.connect(lambda: self.delete_group(group_name))
        layout.addWidget(delete_button)
        
        # 让widget可以接收点击事件（用于选择分组）
        widget.mousePressEvent = lambda event: self.on_group_widget_clicked(group_name, event)
        
        return widget

    def on_group_widget_clicked(self, group_name: str, event):
        """处理分组widget点击事件"""
        # 只有左键点击且不是点击编辑按钮时才切换分组
        if event.button() == Qt.MouseButton.LeftButton:
            self.show_group_features(group_name)

    def on_group_selected(self, item, column):
        """处理分组选择"""
        # 由于使用了自定义widget，这个方法可能不会被调用
        # 分组选择现在通过on_group_widget_clicked处理
        group_name = item.data(0, Qt.UserRole)
        if isinstance(group_name, str):  # 分组项
            self.show_group_features(group_name)

    def show_group_features(self, group_name):
        """显示指定分组的所有功能"""
        self.current_group = group_name
        if self.feature_title:
            self.feature_title.setText(f"📋 功能列表 - {group_name}")
        
        # 清空现有内容
        self.clear_scroll_content()
        
        # 获取分组中的功能
        group = self.feature_manager.get_group(group_name)
        if not group or len(group.features) == 0:
            # 如果分组为空，显示空分组页面
            self.show_empty_group(group_name)
        else:
            # 显示功能卡片，需要计算全局索引
            global_index = 0
            for g in self.feature_manager.groups:
                if g.group_name == group_name:
                    for local_index, feature in enumerate(g.features):
                        feature_card = self.create_feature_card_for_display(feature, global_index)
                        # 恢复之前的选择状态
                        if global_index in self.global_selected_features:
                            feature_card.set_selected(True)
                        if self.scroll_layout:
                            self.scroll_layout.insertWidget(0, feature_card)
                        global_index += 1
                    break
                else:
                    global_index += len(g.features)

    def clear_scroll_content(self):
        """清空滚动区域内容"""
        if not self.scroll_layout:
            return
        while self.scroll_layout.count() > 1:  # 保留最后的stretch
            item = self.scroll_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

    def create_feature_card_for_display(self, feature, index):
        """创建功能卡片用于显示"""
        from ui_components import FeatureCard
        card = FeatureCard(feature, index, self)
        return card

    def filter_features(self):
        """根据搜索框内容过滤功能（支持按分组和名称搜索）"""
        search_text = self.search_box.text().lower()

        if not self.group_tree:
            return

        # 过滤左侧分组导航
        for i in range(self.group_tree.topLevelItemCount()):
            item = self.group_tree.topLevelItem(i)
            if item:
                group_name = item.data(0, Qt.UserRole)
                if group_name:
                    # 检查分组名称是否匹配
                    group_matches = search_text in group_name.lower()
                    
                    # 检查该分组下的功能是否匹配
                    features_by_group = {}
                    for feature in self.feature_manager.features:
                        group = getattr(feature, 'group', '默认')
                        if group not in features_by_group:
                            features_by_group[group] = []
                        features_by_group[group].append(feature)
                    
                    group_features = features_by_group.get(group_name, [])
                    feature_matches = any(
                        search_text in feature.name.lower() 
                        for feature in group_features
                    )
                    
                    # 显示或隐藏分组项
                    item.setHidden(not (group_matches or feature_matches))
        
        # 如果当前显示的分组中有匹配的功能，过滤右侧功能显示
        if self.current_group and self.scroll_layout:
            for i in range(self.scroll_layout.count() - 1):
                layout_item = self.scroll_layout.itemAt(i)
                if layout_item and layout_item.widget():
                    widget = layout_item.widget()
                    if hasattr(widget, 'feature'):
                        feature_matches = search_text in widget.feature.name.lower()
                        widget.setVisible(feature_matches or search_text == "")
                        
        # 更新批量操作按钮状态（因为可见性可能影响选择状态）
        self.update_batch_buttons_state()

    def toggle_select_all(self):
        """切换全选/取消全选"""
        if not self.scroll_layout:
            return
            
        # 检查当前分组中是否所有功能都已选中
        current_group_features = []
        features_by_group = {}
        for i, feature in enumerate(self.feature_manager.features):
            group = getattr(feature, 'group', '默认')
            if group not in features_by_group:
                features_by_group[group] = []
            features_by_group[group].append(i)
        
        current_group_features = features_by_group.get(self.current_group, [])
        
        # 检查当前分组中的功能是否都已选中
        all_current_selected = all(index in self.global_selected_features for index in current_group_features)

        # 根据当前状态切换当前分组的所有功能
        for i in range(self.scroll_layout.count() - 1):
            item = self.scroll_layout.itemAt(i)
            if item and item.widget():
                widget = item.widget()
                if hasattr(widget, 'set_selected'):
                    widget.set_selected(not all_current_selected)

        # 更新按钮文本
        self.batch_select_btn.setText("取消全选" if not all_current_selected else "全选")

    def update_feature_selection_state(self, feature_index: int, is_selected: bool):
        """更新功能的全局选择状态"""
        if is_selected:
            self.global_selected_features.add(feature_index)
        else:
            self.global_selected_features.discard(feature_index)
        
        # 更新批量操作按钮状态
        self.update_batch_buttons_state()

    def clear_all_selections(self):
        """清空所有选择状态"""
        self.global_selected_features.clear()
        
        # 更新当前显示的功能卡片的选择状态
        if self.scroll_layout:
            for i in range(self.scroll_layout.count() - 1):
                item = self.scroll_layout.itemAt(i)
                if item and item.widget():
                    widget = item.widget()
                    if hasattr(widget, 'set_selected'):
                        widget.set_selected(False)
        
        # 更新按钮状态和文本
        self.batch_select_btn.setText("全选")
        self.update_batch_buttons_state()

    def adjust_global_selection_after_deletion(self, deleted_indices):
        """删除功能后调整全局选择状态中的索引"""
        # 将删除的索引排序
        sorted_deleted = sorted(deleted_indices, reverse=True)
        
        # 创建新的选择状态集合
        new_selected = set()
        
        for selected_index in self.global_selected_features:
            if selected_index not in deleted_indices:
                # 计算有多少个更小的索引被删除了
                adjustment = sum(1 for deleted in sorted_deleted if deleted < selected_index)
                new_index = selected_index - adjustment
                new_selected.add(new_index)
        
        # 更新全局选择状态
        self.global_selected_features = new_selected

    def update_batch_buttons_state(self):
        """更新批量操作按钮状态"""
        # 检查全局选择状态中是否有选中的功能
        has_selection = len(self.global_selected_features) > 0

        # 更新按钮状态
        self.batch_delete_btn.setEnabled(has_selection)
        self.batch_export_btn.setEnabled(has_selection)

    def batch_delete_features(self):
        """批量删除选中的功能"""
        # 使用全局选择状态
        selected_indices = list(self.global_selected_features)

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
                
            # 重新调整全局选择状态中的索引（因为删除操作会改变后续功能的索引）
            self.adjust_global_selection_after_deletion(selected_indices)
            
            # 更新显示
            self.update_feature_cards()
            self.batch_select_btn.setText("全选")

    def batch_export_features(self):
        """批量导出选中的功能"""
        # 使用全局选择状态收集选中的功能
        selected_features = []
        all_features = self.feature_manager.get_all_features()
        for index in self.global_selected_features:
            if 0 <= index < len(all_features):
                selected_features.append(all_features[index])

        if not selected_features:
            QMessageBox.warning(self, "提示", "请先选择要导出的功能")
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
                # 按分组组织选中的功能
                groups_dict = {}
                all_features = self.feature_manager.get_all_features()
                
                for index in self.global_selected_features:
                    if 0 <= index < len(all_features):
                        feature = all_features[index]
                        # 找到该功能所属的分组
                        for group in self.feature_manager.groups:
                            if feature in group.features:
                                group_name = group.group_name
                                if group_name not in groups_dict:
                                    groups_dict[group_name] = []
                                groups_dict[group_name].append(feature)
                                break
                
                # 构建新格式的数据
                export_groups = []
                for group_name, features in groups_dict.items():
                    group_data = {
                        'group_name': group_name,
                        'features': [feature.to_dict() for feature in features]
                    }
                    export_groups.append(group_data)
                
                data = {'groups': export_groups}
                
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)

                # 询问是否清空选择状态
                clear_reply = QMessageBox.question(
                    self, "导出完成", 
                    f"成功导出 {len(selected_features)} 个功能到：\n{file_path}\n\n是否清空当前选中状态？",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
                )
                
                if clear_reply == QMessageBox.StandardButton.Yes:
                    self.clear_all_selections()
                    
            except Exception as e:
                QMessageBox.critical(self, "导出失败", f"导出功能失败：{str(e)}")

    def run_feature(self, index: int, repeat_count: int = 1, repeat_interval: float = 1.0):
        """运行指定功能"""
        try:
            all_features = self.feature_manager.get_all_features()
            if 0 <= index < len(all_features):
                feature = all_features[index]

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
                    self.current_feature_index = index
                                        
                    # 开始第一次最小单元执行
                    self._execute_minimal_unit(index)

                except Exception as e:
                    import traceback
                    traceback.print_exc()
                    QMessageBox.critical(self, "错误", f"启动功能执行失败: {str(e)}")
                    # 恢复主窗口
                    self.showNormal()
                    # 更新状态为错误
                    self.update_feature_status(index, "错误")
                    # 清理状态
                    self._reset_repeat_state()
        except Exception as e:
            import traceback
            traceback.print_exc()
            try:
                QMessageBox.critical(self, "严重错误", f"运行功能时发生严重错误: {str(e)}")
                self.showNormal()
                self._reset_repeat_state()
            except BaseException:
                pass

    def _execute_minimal_unit(self, index: int):
        """执行一个最小单元（一次完整功能）"""
        try:
            all_features = self.feature_manager.get_all_features()
            feature = all_features[index]
                        
            # 更新功能卡片状态
            self.update_feature_status(index, "运行中")

            # 清理之前的执行器
            self._cleanup_executor()

            # 创建新的执行器
            self.current_executor = AutomationExecutor(feature.steps, self.window_manager, index)
            
            # 连接信号 - 使用直接方法连接避免lambda闭包
            self.current_executor.step_completed.connect(self.on_step_completed)
            self.current_executor.execution_finished.connect(self._on_minimal_unit_finished)
            self.current_executor.progress_updated.connect(self.on_progress_updated)

            # 最小化主窗口
            self.showMinimized()

            # 激活目标窗口
            self.window_manager.activate_window()
            time.sleep(1.0)  # 等待窗口激活

            # 启动执行器
            self.current_executor.start()
            
        except Exception as e:
            import traceback
            traceback.print_exc()
            self.update_feature_status(index, "错误")
            self.showNormal()
            self._reset_repeat_state()

    def _on_minimal_unit_finished(self, success: bool, message: str):
        """最小单元执行完成处理"""
        index = self.current_feature_index
        
        # 清理当前执行器
        self._cleanup_executor()
        
        if success and self.current_repeat_count < self.target_repeat_count:
            # 需要执行下一个最小单元
            self.current_repeat_count += 1
            
            if self.repeat_interval <= 0:
                # 无间隔，立即执行下一个最小单元
                # 使用QTimer.singleShot避免递归调用
                QTimer.singleShot(0, self._execute_next_unit)
            else:
                # 有间隔，延迟执行
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
            
            self.on_execution_finished(index, success, final_message)
            
            # 重置状态
            self._reset_repeat_state()

    def _cleanup_executor(self):
        """清理当前执行器"""
        if self.current_executor:
            try:
                if self.current_executor.isRunning():
                    self.current_executor.stop()
                    self.current_executor.wait(3000)  # 等待最多3秒
                self.current_executor.deleteLater()
            except Exception as e:
                print(f"清理执行器失败: {e}")
            finally:
                self.current_executor = None

    def _execute_next_unit(self):
        """执行下一个最小单元"""
        if self.current_feature_index >= 0:
            self._execute_minimal_unit(self.current_feature_index)

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

    def pause_feature(self, index: int):
        """暂停指定功能"""
        if 0 <= index < len(self.feature_manager.features):
            # 如果是当前运行的功能，直接控制
            if self.current_feature_index == index and self.current_executor:
                if self.current_executor.running:
                    if self.current_executor.paused:
                        # 恢复执行
                        self.current_executor.resume()
                        self.update_feature_status(index, "运行中")
                    else:
                        # 暂停执行
                        self.current_executor.pause()
                        self.update_feature_status(index, "暂停")
            else:
                # 查找对应的执行器并暂停（向后兼容）
                for thread in self.findChildren(AutomationExecutor):
                    if hasattr(thread, 'feature_index') and thread.feature_index == index:
                        if thread.running:
                            if thread.paused:
                                # 恢复执行
                                thread.resume()
                                self.update_feature_status(index, "运行中")
                            else:
                                # 暂停执行
                                thread.pause()
                                self.update_feature_status(index, "暂停")
                        break

    def update_feature_status(self, index: int, status: str):
        """更新功能状态"""
        if not self.scroll_layout:
            return
            
        # 更新对应的功能卡片状态
        for i in range(self.scroll_layout.count() - 1):
            item = self.scroll_layout.itemAt(i)
            if item and item.widget():
                card = item.widget()
                # 类型检查，确保card是FeatureCard类型
                if hasattr(card, 'index') and hasattr(card, 'set_status') and card.index == index:
                    card.set_status(status)
                    break

    def on_step_completed(self, step_num: int, message: str):
        """步骤完成回调"""
        pass

    def on_execution_finished(self, feature_index: int, success: bool, message: str):
        """执行完成回调"""
        try:
            # 恢复主窗口
            self.showNormal()

            if success:
                self.update_feature_status(feature_index, "停止")
                QMessageBox.information(self, "执行完成", f"功能执行完成: {message}")
            else:
                self.update_feature_status(feature_index, "错误")
                QMessageBox.warning(self, "执行失败", f"功能执行失败: {message}")
        except Exception as e:
            import traceback
            traceback.print_exc()
            # 确保主窗口恢复
            try:
                self.showNormal()
            except BaseException:
                pass

    def on_progress_updated(self, progress: int):
        """进度更新回调"""
        pass

    def stop_feature(self, index: int):
        """停止指定功能"""
        if 0 <= index < len(self.feature_manager.features):
            # 如果是当前运行的功能，直接停止
            if self.current_feature_index == index and self.current_executor:
                self.current_executor.stop()
                self.update_feature_status(index, "停止")
                self._reset_repeat_state()
            else:
                # 查找对应的执行器并停止（向后兼容）
                for thread in self.findChildren(AutomationExecutor):
                    if hasattr(thread, 'feature_index') and thread.feature_index == index:
                        if thread.running:
                            thread.stop()
                            self.update_feature_status(index, "停止")
                        break

    def create_window_binding_section(self, parent_layout):
        """创建窗口绑定区域"""
        group = QGroupBox("窗口绑定")
        layout = QGridLayout(group)

        # 窗口选择下拉框
        self.window_combo = QComboBox()
        self.window_combo.setFixedWidth(200)
        self.window_combo.currentIndexChanged.connect(self.on_window_selected)
        # 延迟加载窗口列表，确保UI组件已创建
        QTimer.singleShot(100, self.refresh_window_list)

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
        # 暂时断开信号连接，避免触发选择事件
        self.window_combo.currentIndexChanged.disconnect()

        self.window_combo.clear()
        self.window_combo.addItem("请选择窗口", None)  # 添加默认选项

        windows = self.window_manager.get_window_list()
        for window in windows:
            self.window_combo.addItem(window['title'], window['handle'])

        # 重新连接信号
        self.window_combo.currentIndexChanged.connect(self.on_window_selected)

    def on_window_selected(self, index):
        """窗口选择变化处理"""
        if index <= 0:  # 默认选项
            self.update_binding_status(False)
            return

        window_handle = self.window_combo.currentData()
        if window_handle and self.window_manager.bind_window(window_handle):
            self.update_binding_status(True)
            # 设置主窗口在绑定窗口之上
            QTimer.singleShot(200, self.set_main_window_above_bound_window)
        else:
            self.window_combo.setCurrentIndex(0)  # 重置为默认选项
            self.update_binding_status(False)
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
                        win32gui.SetWindowPos(
                            self.window_manager.window_handle,  # 绑定窗口
                            main_hwnd,  # 主窗口句柄（作为参考窗口）
                            0, 0, 0, 0,  # 位置和大小保持不变
                            win32con.SWP_NOMOVE | win32con.SWP_NOSIZE | win32con.SWP_NOACTIVATE
                        )
                    except Exception as e1:
                        # 方法2：使用BringWindowToTop
                        try:
                            win32gui.BringWindowToTop(main_hwnd)
                        except Exception as e2:
                            # 方法3：使用SetForegroundWindow
                            try:
                                win32gui.SetForegroundWindow(main_hwnd)
                            except Exception as e3:
                                QMessageBox.warning(
                                    self, "警告", "无法自动调整绑定窗口到当前主窗口之上，请手动操作")
        except Exception as e:
            QMessageBox.warning(self, "错误", f"设置窗口层级失败: {str(e)}")

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
        self.coordinate_label.setStyleSheet(
            "font-family: monospace; font-size: 14px;")
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

    def setup_tray_icon(self):
        """设置系统托盘图标"""
        # 检查系统是否支持托盘图标
        if not QSystemTrayIcon.isSystemTrayAvailable():
            QMessageBox.critical(None, "系统托盘", "系统不支持托盘图标功能")
            self.tray_icon = None
            return
            
        try:

            # 创建托盘图标
            self.tray_icon = QSystemTrayIcon(self)
            self.tray_icon.setToolTip("自动化操作工具")
            
            # 设置托盘图标
            try:
                icon = QIcon("R.ico")
                if not icon.isNull():
                    self.tray_icon.setIcon(icon)
                else:
                    # 如果图标文件不存在，使用默认图标
                    self.tray_icon.setIcon(self.style().standardIcon(self.style().StandardPixmap.SP_ComputerIcon))
            except Exception as e:
                print(f"设置托盘图标失败: {e}")
                # 使用默认图标
                self.tray_icon.setIcon(self.style().standardIcon(self.style().StandardPixmap.SP_ComputerIcon))

            # 创建托盘菜单
            tray_menu = QMenu()

            # 显示主窗口动作
            show_action = tray_menu.addAction("🏠 显示主窗口")
            show_action.triggered.connect(self.show_main_window)

            tray_menu.addSeparator()
            
            # 应用信息
            info_action = tray_menu.addAction("ℹ️ 关于程序")
            info_action.triggered.connect(self.show_about_dialog)

            tray_menu.addSeparator()

            # 退出动作
            quit_action = tray_menu.addAction("❌ 退出程序")
            quit_action.triggered.connect(self.quit_application)

            # 设置托盘菜单
            self.tray_icon.setContextMenu(tray_menu)

            # 连接托盘图标点击事件
            self.tray_icon.activated.connect(self.on_tray_icon_activated)

            # 显示托盘图标
            self.tray_icon.show()

        except Exception as e:
            print(f"设置托盘图标失败: {e}")
            self.tray_icon = None

    def show_main_window(self):
        """显示主窗口"""
        self.showNormal()
        self.activateWindow()
        self.raise_()
    
    def show_about_dialog(self):
        """显示关于对话框"""
        QMessageBox.about(
            self,
            "关于 - 自动化操作工具",
            """
<h3>自动化操作工具 v1.0</h3>
<p>一个功能强大的Windows自动化操作工具</p>
<p><b>主要功能：</b></p>
<ul>
<li>🖱️ 鼠标点击自动化</li>
<li>⌨️ 键盘输入自动化</li>
<li>📁 功能分组管理</li>
<li>📤 批量导入导出</li>
<li>🔄 重复执行控制</li>
<li>💾 数据持久化存储</li>
</ul>
<p><b>使用提示：</b></p>
<p>• 程序最小化到系统托盘后仍在后台运行</p>
<p>• 双击托盘图标可重新显示主窗口</p>
<p>• 右键托盘图标查看更多选项</p>
            """
        )

    def quit_application(self):
        """退出应用程序"""
        # 清理所有资源
        self._cleanup_executor()
        self._reset_repeat_state()
        if self.coordinate_capture:
            self.coordinate_capture.stop_capture()
        QApplication.quit()

    def on_tray_icon_activated(self, reason):
        """托盘图标激活事件"""
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self.show_main_window()
        elif reason == QSystemTrayIcon.ActivationReason.Trigger:
            # 单击也显示窗口（左键单击）
            self.show_main_window()

    def closeEvent(self, event):
        """重写关闭事件，最小化到托盘而不是退出"""
        # 先清理资源
        self._cleanup_executor()
        self._reset_repeat_state()
        
        if self.tray_icon and self.tray_icon.isVisible():
            self.hide()
            # 只在第一次最小化时显示提示
            if not self.tray_notification_shown:
                self.tray_icon.showMessage(
                    "自动化操作工具",
                    "程序已最小化到系统托盘。双击托盘图标或右键选择'显示主窗口'来重新打开。",
                    QSystemTrayIcon.MessageIcon.Information,
                    3000
                )
                self.tray_notification_shown = True
            event.ignore()
        else:
            # 如果托盘不可用，询问用户是否真的要退出
            reply = QMessageBox.question(
                self, 
                "确认退出", 
                "系统托盘不可用，关闭窗口将完全退出程序。\n确定要退出吗？",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            if reply == QMessageBox.StandardButton.Yes:
                event.accept()
            else:
                event.ignore()

    def setup_connections(self):
        """设置信号连接"""
        # 步骤列表选择变化
        self.steps_list.itemSelectionChanged.connect(
            self.on_step_selection_changed)

        # 坐标捕获信号连接
        self.coordinate_capture.coordinate_captured.connect(
            self.on_coordinate_captured)
        self.coordinate_capture.capture_cancelled.connect(
            self.on_capture_cancelled)
        self.coordinate_capture.capture_restored.connect(
            self.on_capture_restored)

    def on_coordinate_captured(self, x: float, y: float):
        """坐标捕获成功处理"""
        try:
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
            import traceback
            traceback.print_exc()

    def _show_step_edit_dialog(self, x: float, y: float):
        """延迟显示步骤编辑对话框"""
        try:

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

        except Exception as e:
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

    def toggle_coordinate_capture(self):
        """切换坐标捕获状态"""
        if self.capture_button_is_capturing:
            # 停止捕获
            self.coordinate_capture.stop_capture()
            self.capture_button.setText("获取坐标")
            self.capture_status_label.setText("点击按钮后移动鼠标到目标位置并点击左键，按ESC取消")
            self.capture_button_is_capturing = False
        else:
            # 开始捕获
            if self.coordinate_capture.start_capture():
                # 开始捕获时激活目标窗口
                self.window_manager.activate_window()
                self.capture_button.setText("停止捕获")
                self.capture_status_label.setText(
                    "正在捕获坐标，请移动鼠标到目标位置并点击左键，按ESC取消")
                self.capture_button_is_capturing = True
            else:
                QMessageBox.warning(self, "错误", "请先绑定窗口")

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
                dialog.move(
                    cursor_pos.x() - dialog.width() // 2,
                    cursor_pos.y() - dialog.height() // 2)

                if dialog.exec() == QDialog.DialogCode.Accepted:
                    self.automation_steps[index] = dialog.get_step()
                    self.refresh_steps_list()
                else:
                    # 如果是新添加的步骤且用户取消编辑，则删除该步骤
                    if index == len(self.automation_steps) - 1 and not step.action:
                        del self.automation_steps[index]
                        self.refresh_steps_list()
            except Exception as e:
                print(f"编辑步骤错误: {e}")

    def delete_step(self, index: int):
        """删除步骤"""
        if 0 <= index < len(self.automation_steps):
            del self.automation_steps[index]
            self.refresh_steps_list()

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

    def save_as_feature(self):
        """保存为功能"""
        if not self.automation_steps:
            QMessageBox.warning(self, "警告", "没有可保存的步骤")
            return

        # 创建功能编辑对话框
        dialog = FeatureDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            feature_data = dialog.get_feature()
            # 创建功能对象
            feature = AutomationFeature(feature_data.name, self.automation_steps.copy())
            # 添加到指定分组
            group_name = getattr(feature_data, 'group', '默认')
            self.feature_manager.add_feature_to_group(feature, group_name)
            self.update_feature_list()

    def update_feature_list(self):
        """更新功能列表显示（兼容旧接口）"""
        self.update_feature_cards()

    def edit_feature_by_index(self, index: int):
        """通过索引编辑功能"""
        try:
            group, local_index, feature = self.feature_manager.get_feature_by_global_index(index)
            
            # 创建一个临时的功能数据对象用于对话框
            class TempFeatureData:
                def __init__(self, name, steps, group):
                    self.name = name
                    self.steps = steps
                    self.group = group
            
            temp_feature = TempFeatureData(feature.name, feature.steps, group.group_name)
            
            dialog = FeatureDialog(self, temp_feature)
            if dialog.exec() == QDialog.DialogCode.Accepted:
                feature_data = dialog.get_feature()
                # 创建更新后的功能
                updated_feature = AutomationFeature(feature_data.name, feature_data.steps)
                new_group_name = getattr(feature_data, 'group', '默认')
                
                # 更新功能
                self.feature_manager.update_feature(index, updated_feature, new_group_name)
                self.update_feature_list()
        except IndexError:
            QMessageBox.warning(self, "错误", "功能不存在")
            self.update_feature_list()

    def delete_feature_by_index(self, index: int):
        """通过索引删除功能"""
        try:
            group, local_index, feature = self.feature_manager.get_feature_by_global_index(index)
            reply = QMessageBox.question(
                self, "确认删除", f"确定要删除功能 '{feature.name}' 吗？",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply == QMessageBox.StandardButton.Yes:
                self.feature_manager.delete_feature(index)
                self.update_feature_list()
        except IndexError:
            QMessageBox.warning(self, "错误", "功能不存在")
            self.update_feature_list()

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
                if isinstance(data, dict) and 'groups' in data:
                    try:
                        imported_groups = [FeatureGroup.from_dict(group_data) for group_data in data['groups']]
                        total_features = sum(len(group.features) for group in imported_groups)
                        
                        if total_features == 0:
                            QMessageBox.warning(self, "警告", "导入的文件中没有功能")
                            return
                        
                        # 询问是否覆盖现有功能
                        current_features = self.feature_manager.get_all_features()
                        if current_features:
                            reply = QMessageBox.question(
                                self, "导入确认",
                                f"将导入 {total_features} 个功能（{len(imported_groups)} 个分组）。\n是否覆盖现有功能？\n\n是：覆盖现有功能\n否：追加到现有功能",
                                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No | QMessageBox.StandardButton.Cancel
                            )

                            if reply == QMessageBox.StandardButton.Cancel:
                                return
                            elif reply == QMessageBox.StandardButton.Yes:
                                # 覆盖现有功能
                                self.feature_manager.groups = imported_groups
                            else:
                                # 追加到现有功能
                                for group in imported_groups:
                                    for feature in group.features:
                                        self.feature_manager.add_feature_to_group(feature, group.group_name)
                        else:
                            # 没有现有功能，直接导入
                            self.feature_manager.groups = imported_groups

                        # 保存并更新显示
                        self.feature_manager.save_features()
                        self.update_feature_cards()
                        QMessageBox.information(
                            self, "成功", f"成功导入 {total_features} 个功能（{len(imported_groups)} 个分组）")
                            
                    except Exception as e:
                        QMessageBox.critical(self, "导入失败", f"解析导入文件失败：{str(e)}")
                else:
                    QMessageBox.warning(self, "错误", "文件格式不正确")

        except Exception as e:
            QMessageBox.critical(self, "导入失败", f"导入功能失败：{str(e)}")

    def export_features(self):
        """导出功能"""
        try:
            all_features = self.feature_manager.get_all_features()
            if not all_features:
                QMessageBox.warning(self, "警告", "没有可导出的功能")
                return

            # 选择保存位置
            file_path, _ = QFileDialog.getSaveFileName(
                self,
                "导出功能文件",
                "automation_features_export.json",
                "JSON文件 (*.json);;所有文件 (*)"
            )

            if file_path:
                # 使用新的分组格式导出
                data = {
                    'groups': [group.to_dict() for group in self.feature_manager.groups]
                }
                
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)

                QMessageBox.information(
                    self, "成功", f"成功导出 {len(all_features)} 个功能到：\n{file_path}")

        except Exception as e:
            QMessageBox.critical(self, "导出失败", f"导出功能失败：{str(e)}")

    def on_step_selection_changed(self):
        """步骤选择变化处理"""
        pass  # 编辑和删除按钮已删除，不再需要处理

    def add_new_group(self):
        """新增分组"""
        try:
            dialog = GroupDialog(self)
            
            # 居中显示对话框
            screen_geo = QApplication.primaryScreen().geometry()
            dialog.move(
                screen_geo.center().x() - dialog.width() // 2,
                screen_geo.center().y() - dialog.height() // 2
            )
            
            if dialog.exec() == QDialog.DialogCode.Accepted:
                group_name = dialog.get_group_name()
                if group_name:
                    # 检查分组名称是否已存在
                    existing_groups = self.feature_manager.get_all_groups()
                    
                    if group_name in existing_groups:
                        QMessageBox.warning(self, "警告", f"分组 '{group_name}' 已存在，请使用其他名称")
                        return
                    
                    # 添加空分组到FeatureManager
                    self.feature_manager.add_empty_group(group_name)
                    
                    # 更新分组导航显示
                    self.update_group_navigation()
                    
                    # 选中新创建的分组
                    if self.group_tree:
                        for i in range(self.group_tree.topLevelItemCount()):
                            item = self.group_tree.topLevelItem(i)
                            if item and item.data(0, Qt.UserRole) == group_name:
                                self.group_tree.setCurrentItem(item)
                                self.show_empty_group(group_name)
                                break

        except Exception as e:
            import traceback
            traceback.print_exc()
            QMessageBox.critical(self, "错误", f"创建分组失败：{str(e)}")

    def show_empty_group(self, group_name: str):
        """显示空分组页面"""
        self.current_group = group_name
        if self.feature_title:
            self.feature_title.setText(f"📋 功能列表 - {group_name}")
        
        # 清空现有内容
        self.clear_scroll_content()
        
        # 显示空分组提示
        empty_label = QLabel("此分组暂无功能\n\n您可以通过以下方式添加功能到此分组：\n1. 在操作配置页面创建新功能时选择此分组\n2. 编辑现有功能并更改其分组")
        empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        empty_label.setStyleSheet("""
            QLabel {
                color: #6c757d;
                font-size: 14px;
                padding: 40px;
                background-color: #f8f9fa;
                border: 2px dashed #dee2e6;
                border-radius: 8px;
                margin: 20px;
            }
        """)
        if self.scroll_layout:
            self.scroll_layout.insertWidget(0, empty_label)

    def edit_group_name(self, old_group_name: str):
        """编辑分组名称"""
        try:
            dialog = GroupDialog(self, old_group_name)
            
            # 居中显示对话框
            screen_geo = QApplication.primaryScreen().geometry()
            dialog.move(
                screen_geo.center().x() - dialog.width() // 2,
                screen_geo.center().y() - dialog.height() // 2
            )
            
            if dialog.exec() == QDialog.DialogCode.Accepted:
                new_group_name = dialog.get_group_name()
                if new_group_name and new_group_name != old_group_name:
                    # 检查新分组名称是否已存在
                    existing_groups = self.feature_manager.get_all_groups()
                    
                    if new_group_name in existing_groups:
                        QMessageBox.warning(self, "警告", f"分组 '{new_group_name}' 已存在，请使用其他名称")
                        return
                    
                    # 重命名分组
                    success = self.feature_manager.rename_group(old_group_name, new_group_name)
                    
                    if success:
                        # 更新分组导航显示
                        self.update_group_navigation()
                        
                        # 如果当前显示的是被重命名的分组，更新显示
                        if self.current_group == old_group_name:
                            self.current_group = new_group_name
                            self.show_group_features(new_group_name)
                        
                        QMessageBox.information(self, "成功", f"分组已重命名为 '{new_group_name}'")
                    else:
                        QMessageBox.warning(self, "错误", "重命名分组失败")
                        
        except Exception as e:
            import traceback
            traceback.print_exc()
            QMessageBox.critical(self, "错误", f"编辑分组名称失败：{str(e)}")

    def delete_group(self, group_name: str):
        """删除分组"""
        try:
            # 检查是否为默认分组
            if group_name == '默认':
                QMessageBox.warning(self, "警告", "默认分组不能删除")
                return
            
            # 获取分组信息
            group = self.feature_manager.get_group(group_name)
            if not group:
                QMessageBox.warning(self, "错误", f"分组 '{group_name}' 不存在")
                return
            
            feature_count = group.get_feature_count()
            
            if feature_count > 0:
                # 分组中有功能，询问用户如何处理
                reply = QMessageBox.question(
                    self, "确认删除", 
                    f"分组 '{group_name}' 中包含 {feature_count} 个功能。\n\n"
                    "删除分组会将其中的功能移动到'默认'分组。\n\n"
                    "确定要删除此分组吗？",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                    QMessageBox.StandardButton.No
                )
                
                if reply != QMessageBox.StandardButton.Yes:
                    return
                
                # 将分组中的功能移动到默认分组
                default_group = self.feature_manager.get_or_create_group('默认')
                for feature in group.features.copy():  # 使用copy避免迭代时修改列表
                    default_group.add_feature(feature)
                
                # 清空原分组
                group.features.clear()
                
            else:
                # 空分组，直接确认删除
                reply = QMessageBox.question(
                    self, "确认删除", 
                    f"确定要删除分组 '{group_name}' 吗？",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                    QMessageBox.StandardButton.No
                )
                
                if reply != QMessageBox.StandardButton.Yes:
                    return
            
            # 删除分组
            success = self.feature_manager.delete_group(group_name)
            
            if success:
                # 更新分组导航显示
                self.update_group_navigation()
                
                # 如果当前显示的是被删除的分组，切换到默认分组
                if self.current_group == group_name:
                    self.current_group = '默认'
                    self.show_group_features('默认')
                
                if feature_count > 0:
                    QMessageBox.information(self, "删除成功", 
                        f"分组 '{group_name}' 已删除，其中的 {feature_count} 个功能已移动到'默认'分组")
                else:
                    QMessageBox.information(self, "删除成功", f"分组 '{group_name}' 已删除")
            else:
                QMessageBox.warning(self, "错误", "删除分组失败")
                
        except Exception as e:
            import traceback
            traceback.print_exc()
            QMessageBox.critical(self, "错误", f"删除分组失败：{str(e)}")


def main():
    """主函数"""
    app = QApplication(sys.argv)
    app.setApplicationName("dao")
    app.setApplicationVersion("1.0")

    # 设置应用程序图标（如果有的话）
    app.setWindowIcon(QIcon("R.ico"))   

    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main() 