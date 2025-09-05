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
    QDialog, QFileDialog, QTabWidget, QScrollArea, QSystemTrayIcon
)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QCursor
import win32gui
import win32con

# 导入自定义模块
from window_manager import WindowManager
from coordinate_capture import CoordinateCapture
from automation import AutomationStep, AutomationFeature, FeatureManager, AutomationExecutor
from ui_components import StepListWidget, FeatureCardWidget, GroupCard
from dialogs import FeatureDialog, StepEditDialog


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

        # 添加一个标志，表示是否正在编辑
        self.is_editing: bool = False

        # 添加按钮状态标志
        self.capture_button_is_capturing: bool = False

        # 添加托盘图标
        self.tray_icon: Optional[QSystemTrayIcon] = None
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

        # 功能卡片容器区域
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
        self.feature_cards_layout.setSpacing(12)
        self.feature_cards_layout.addStretch()

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
        """更新功能卡片显示（使用可折叠分组卡片）"""
        # 清除旧的卡片，但保留最后的弹性空间
        while self.feature_cards_layout.count() > 1:
            item = self.feature_cards_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        # 按分组组织功能
        features_by_group = {}
        for i, feature in enumerate(self.feature_manager.features):
            group = getattr(feature, 'group', '默认')
            if group not in features_by_group:
                features_by_group[group] = []
            features_by_group[group].append((i, feature))

        # 按分组名称排序
        sorted_groups = sorted(features_by_group.keys())

        # 为每个分组创建分组卡片
        for group_name in sorted_groups:
            group_features = features_by_group[group_name]
            group_card = GroupCard(group_name, group_features, self)
            # 在弹性空间之前插入分组卡片
            self.feature_cards_layout.insertWidget(
                self.feature_cards_layout.count() - 1, group_card)

    def filter_features(self):
        """根据搜索框内容过滤功能（支持按分组和名称搜索）"""
        search_text = self.search_box.text().lower()

        # 遍历所有分组卡片
        for i in range(self.feature_cards_layout.count() - 1):
            item = self.feature_cards_layout.itemAt(i)
            if item and item.widget():
                widget = item.widget()
                
                # 如果是分组卡片
                if hasattr(widget, 'group_name'):
                    # 检查分组名称是否匹配
                    group_matches = search_text in widget.group_name.lower()
                    
                    # 检查该分组下的功能是否匹配
                    feature_cards = widget.get_feature_cards()
                    feature_matches = any(
                        search_text in card.feature.name.lower() 
                        for card in feature_cards
                    )
                    
                    # 如果分组名称或功能名称匹配，显示分组卡片
                    if group_matches or feature_matches:
                        widget.set_visible(True)
                        # 如果分组名称不匹配但功能匹配，展开分组
                        if not group_matches and feature_matches:
                            widget.is_collapsed = True
                            widget.toggle_collapse()
                    else:
                        widget.set_visible(False)

    def toggle_select_all(self):
        """切换全选/取消全选"""
        # 检查当前是否有选中的卡片
        all_selected = True
        for i in range(self.feature_cards_layout.count() - 1):
            item = self.feature_cards_layout.itemAt(i)
            if item and item.widget():
                widget = item.widget()
                # 只检查分组卡片中的功能卡片
                if hasattr(widget, 'group_name'):
                    feature_cards = widget.get_feature_cards()
                    for card in feature_cards:
                        if hasattr(card, 'is_selected') and not card.is_selected:
                            all_selected = False
                            break
                    if not all_selected:
                        break

        # 根据当前状态切换
        for i in range(self.feature_cards_layout.count() - 1):
            item = self.feature_cards_layout.itemAt(i)
            if item and item.widget():
                widget = item.widget()
                # 只处理分组卡片中的功能卡片
                if hasattr(widget, 'group_name'):
                    feature_cards = widget.get_feature_cards()
                    for card in feature_cards:
                        if hasattr(card, 'set_selected'):
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
                widget = item.widget()
                # 只检查分组卡片中的功能卡片
                if hasattr(widget, 'group_name'):
                    feature_cards = widget.get_feature_cards()
                    for card in feature_cards:
                        if hasattr(card, 'is_selected') and hasattr(card, 'isVisible') and card.is_selected and card.isVisible():
                            has_selection = True
                            break
                    if has_selection:
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
                widget = item.widget()
                # 只检查分组卡片中的功能卡片
                if hasattr(widget, 'group_name'):
                    feature_cards = widget.get_feature_cards()
                    for card in feature_cards:
                        if hasattr(card, 'is_selected') and hasattr(card, 'index') and hasattr(card, 'isVisible') and card.is_selected and card.isVisible():
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
                card: FeatureCardWidget = item.widget()
                if hasattr(card, 'is_selected') and hasattr(card, 'feature') and hasattr(card, 'isVisible') and card.is_selected and card.isVisible():
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

                QMessageBox.information(
                    self, "成功", f"成功导出 {len(selected_features)} 个功能到：\n{file_path}")
            except Exception as e:
                QMessageBox.critical(self, "导出失败", f"导出功能失败：{str(e)}")

    def run_feature(self, index: int, repeat_count: int = 1, repeat_interval: float = 1.0):
        """运行指定功能"""
        print(f"[DEBUG] 开始运行功能 {index}，执行次数: {repeat_count}，间隔: {repeat_interval}秒")
        try:
            if 0 <= index < len(self.feature_manager.features):
                feature = self.feature_manager.features[index]
                print(f"[DEBUG] 功能名称: {feature.name}, 步骤数: {len(feature.steps)}")

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
                    
                    print(f"[DEBUG] 设置执行参数: 次数={repeat_count}, 间隔={repeat_interval}秒")
                    
                    # 开始第一次最小单元执行
                    self._execute_minimal_unit(index)

                except Exception as e:
                    print(f"启动功能执行失败: {e}")
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
            print(f"运行功能总体错误: {e}")
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
            feature = self.feature_manager.features[index]
            
            print(f"[MINIMAL_UNIT] 开始第 {self.current_repeat_count}/{self.target_repeat_count} 次执行")
            
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
            print(f"[MINIMAL_UNIT] 最小单元执行器已启动")
            
        except Exception as e:
            print(f"[MINIMAL_UNIT] 启动最小单元失败: {e}")
            import traceback
            traceback.print_exc()
            self.update_feature_status(index, "错误")
            self.showNormal()
            self._reset_repeat_state()

    def _on_minimal_unit_finished(self, success: bool, message: str):
        """最小单元执行完成处理"""
        index = self.current_feature_index
        print(f"[MINIMAL_UNIT] 第 {self.current_repeat_count}/{self.target_repeat_count} 次执行完成: {success}")
        
        # 清理当前执行器
        self._cleanup_executor()
        
        if success and self.current_repeat_count < self.target_repeat_count:
            # 需要执行下一个最小单元
            self.current_repeat_count += 1
            
            if self.repeat_interval <= 0:
                # 无间隔，立即执行下一个最小单元
                print("[MINIMAL_UNIT] 无间隔，立即开始下一次")
                # 使用QTimer.singleShot避免递归调用
                QTimer.singleShot(0, self._execute_next_unit)
            else:
                # 有间隔，延迟执行
                print(f"[MINIMAL_UNIT] 等待 {self.repeat_interval} 秒后执行下一次")
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
            
            print(f"[MINIMAL_UNIT] 最终结果: {final_message}")
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
        # 更新对应的功能卡片状态
        for i in range(self.feature_cards_layout.count() - 1):
            item = self.feature_cards_layout.itemAt(i)
            if item and item.widget():
                card: FeatureCardWidget = item.widget()
                # 类型检查，确保card是FeatureCard类型
                if hasattr(card, 'index') and hasattr(card, 'set_status') and card.index == index:
                    card.set_status(status)
                    break

    def on_step_completed(self, step_num: int, message: str):
        """步骤完成回调"""
        print(f"[SIGNAL] 功能 {self.current_feature_index} 步骤 {step_num} 完成: {message}")

    def on_execution_finished(self, feature_index: int, success: bool, message: str):
        """执行完成回调"""
        try:
            print(f"[SIGNAL] 执行完成回调: 功能 {feature_index}, 成功: {success}, 消息: {message}")
            # 恢复主窗口
            print("[SIGNAL] 恢复主窗口...")
            self.showNormal()
            print("[SIGNAL] 主窗口已恢复")

            if success:
                print("[SIGNAL] 更新功能状态为'停止'")
                self.update_feature_status(feature_index, "停止")
                print("[SIGNAL] 显示成功消息框")
                QMessageBox.information(self, "执行完成", f"功能执行完成: {message}")
            else:
                print("[SIGNAL] 更新功能状态为'错误'")
                self.update_feature_status(feature_index, "错误")
                print("[SIGNAL] 显示失败消息框")
                QMessageBox.warning(self, "执行失败", f"功能执行失败: {message}")
        except Exception as e:
            print(f"[SIGNAL] 执行完成回调错误: {e}")
            import traceback
            traceback.print_exc()
            # 确保主窗口恢复
            try:
                self.showNormal()
            except BaseException:
                print("[SIGNAL] 恢复主窗口失败")
                pass

    def on_progress_updated(self, progress: int):
        """进度更新回调"""
        print(f"[SIGNAL] 功能 {self.current_feature_index} 进度: {progress}%")

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
                        print("绑定窗口已设置在主窗口之下")
                    except Exception as e1:
                        print(f"方法1失败: {e1}")
                        # 方法2：使用BringWindowToTop
                        try:
                            win32gui.BringWindowToTop(main_hwnd)
                            print("主窗口已置顶（方法2）")
                        except Exception as e2:
                            print(f"方法2失败: {e2}")
                            # 方法3：使用SetForegroundWindow
                            try:
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
        try:
            from PySide6.QtWidgets import QSystemTrayIcon, QMenu
            from PySide6.QtGui import QIcon

            # 创建托盘图标
            self.tray_icon = QSystemTrayIcon(self)
            self.tray_icon.setToolTip("自动化操作工具")

            # 创建托盘菜单
            tray_menu = QMenu()

            # 显示主窗口动作
            show_action = tray_menu.addAction("显示主窗口")
            show_action.triggered.connect(self.show_main_window)

            tray_menu.addSeparator()

            # 退出动作
            quit_action = tray_menu.addAction("退出")
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

    def closeEvent(self, event):
        """重写关闭事件，最小化到托盘而不是退出"""
        # 先清理资源
        self._cleanup_executor()
        self._reset_repeat_state()
        
        if self.tray_icon and self.tray_icon.isVisible():
            self.hide()
            self.tray_icon.showMessage(
                "自动化操作工具",
                "程序已最小化到系统托盘",
                QSystemTrayIcon.MessageIcon.Information,
                2000
            )
            event.ignore()
        else:
            event.accept()

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
            feature = dialog.get_feature()
            # 将当前步骤复制到功能中
            feature.steps = self.automation_steps.copy()
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
                    imported_features = [AutomationFeature.from_dict(
                        feature_data) for feature_data in data]

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
                    QMessageBox.information(
                        self, "成功", f"成功导入 {len(imported_features)} 个功能")
                else:
                    QMessageBox.warning(self, "错误", "文件格式不正确")

        except Exception as e:
            QMessageBox.critical(self, "导入失败", f"导入功能失败：{str(e)}")

    def export_features(self):
        """导出功能"""
        try:
            if not self.feature_manager.features:
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
                data = [feature.to_dict() for feature in self.feature_manager.features]
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)

                QMessageBox.information(
                    self, "成功", f"成功导出 {len(self.feature_manager.features)} 个功能到：\n{file_path}")

        except Exception as e:
            QMessageBox.critical(self, "导出失败", f"导出功能失败：{str(e)}")

    def on_step_selection_changed(self):
        """步骤选择变化处理"""
        pass  # 编辑和删除按钮已删除，不再需要处理


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