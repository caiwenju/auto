#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from typing import Optional, Union, List
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QListWidget, QListWidgetItem, QCheckBox, QSpinBox, QDoubleSpinBox
)
from PySide6.QtCore import Qt, QEvent

from automation import AutomationStep, AutomationFeature


# 类型别名，用于帮助IDE识别FeatureCard
FeatureCardWidget = Union['FeatureCard', QWidget]


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
        self.step: AutomationStep = step
        self.index: int = index
        self.parent = parent
        self.init_ui()

    def init_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(5, 2, 5, 2)

        # 步骤信息
        step_text = f"步骤 {self.index + 1}: "
        
        # 添加步骤名称（如果有）
        if hasattr(self.step, 'name') and self.step.name:
            step_text += f"{self.step.name}"
        else:
            step_text += f"({self.step.x:.1%}, {self.step.y:.1%}) - {self.step.action}"
            
        # 添加其他信息
        if self.step.delay > 0:
            step_text += f" [延迟: {self.step.delay}s]"
        if self.step.text:
            step_text += f" [文本: {self.step.text}]"
        if self.step.action in ["左键多击", "右键多击"] and hasattr(
                self.step, 'click_count') and self.step.click_count > 1:
            step_text += f" [次数: {self.step.click_count}]"
            if hasattr(
                    self.step,
                    'click_interval') and self.step.click_interval != 0.05:
                step_text += f" [间隔: {self.step.click_interval}s]"
        
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
            delete_btn.clicked.connect(
                lambda: self.parent.delete_step(
                    self.index))
        layout.addWidget(delete_btn)


class FeatureCard(QWidget):
    """功能卡片组件"""

    def __init__(self, feature: AutomationFeature, index: int, parent=None):
        super().__init__()
        self.feature: AutomationFeature = feature
        self.index: int = index
        self.parent = parent
        self.status: str = "停止"  # 默认状态：停止、运行中、暂停、错误
        self.is_selected: bool = False
        self.is_hovered: bool = False

        # UI组件
        self.checkbox: Optional[QCheckBox] = None
        self.status_label: Optional[QLabel] = None
        self.run_btn: Optional[QPushButton] = None
        self.pause_btn: Optional[QPushButton] = None
        self.stop_btn: Optional[QPushButton] = None
        self.edit_btn: Optional[QPushButton] = None
        self.delete_btn: Optional[QPushButton] = None

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
        name_label.setStyleSheet(
            "font-size: 16px; font-weight: bold; color: #212529;")
        top_layout.addWidget(name_label)

        # 分组信息
        if hasattr(self.feature, 'group') and self.feature.group:
            group_label = QLabel(f"[{self.feature.group}]")
            group_label.setStyleSheet(
                "color: #6c757d; font-size: 12px; padding: 2px 6px; border-radius: 4px; background-color: #e9ecef;")
            top_layout.addWidget(group_label)

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
        
        # 执行参数设置
        params_layout = QVBoxLayout()
        
        # 执行次数
        repeat_layout = QHBoxLayout()
        repeat_layout.addWidget(QLabel("执行次数:"))
        self.repeat_count = QSpinBox()
        self.repeat_count.setMinimum(1)
        self.repeat_count.setMaximum(99999999)  # 限制最大值为99999，避免过大值导致问题
        self.repeat_count.setValue(1)
        self.repeat_count.setFixedWidth(80)
        self.repeat_count.setToolTip("设置功能执行的次数")
        repeat_layout.addWidget(self.repeat_count)
        repeat_layout.addStretch()
        params_layout.addLayout(repeat_layout)
        
        # 执行间隔
        interval_layout = QHBoxLayout()
        interval_layout.addWidget(QLabel("间隔时间:"))
        self.repeat_interval = QDoubleSpinBox()
        self.repeat_interval.setMinimum(0.0)
        self.repeat_interval.setMaximum(99999999.0)
        self.repeat_interval.setValue(1.0)
        self.repeat_interval.setDecimals(1)
        self.repeat_interval.setSuffix(" 秒")
        self.repeat_interval.setFixedWidth(80)
        self.repeat_interval.setToolTip("设置每次执行之间的间隔时间（秒）")
        interval_layout.addWidget(self.repeat_interval)
        interval_layout.addStretch()
        params_layout.addLayout(interval_layout)
        
        button_layout.addLayout(params_layout)
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
        self.run_btn.clicked.connect(
            lambda: self._call_parent_method(
                'run_feature', self.index, self.repeat_count.value(), self.repeat_interval.value()))
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
        self.pause_btn.clicked.connect(self.on_pause_btn_clicked)
        self.pause_btn.setEnabled(False)  # 初始状态禁用
        button_layout.addWidget(self.pause_btn)

        # 停止按钮
        self.stop_btn = QPushButton("停止")
        self.stop_btn.setObjectName("cardStopBtn")
        self.stop_btn.setFixedSize(60, 28)
        self.stop_btn.setStyleSheet("""
            QPushButton#cardStopBtn {
                background-color: #dc3545;
                color: white;
                border: none;
                border-radius: 4px;
                font-size: 12px;
            }
            QPushButton#cardStopBtn:hover {
                background-color: #c82333;
            }
            QPushButton#cardStopBtn:pressed {
                background-color: #bd2130;
            }
            QPushButton#cardStopBtn:disabled {
                background-color: #f8f9fa;
                color: #6c757d;
                border: 1px solid #ced4da;
            }
        """)
        self.stop_btn.clicked.connect(
            lambda: self._call_parent_method(
                'stop_feature', self.index))
        self.stop_btn.setEnabled(False)  # 初始状态禁用
        button_layout.addWidget(self.stop_btn)

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
        self.edit_btn.clicked.connect(
            lambda: self._call_parent_method(
                'edit_feature_by_index', self.index))
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
        self.delete_btn.clicked.connect(
            lambda: self._call_parent_method(
                'delete_feature_by_index', self.index))
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
        self._call_parent_method('update_batch_buttons_state')

    def on_checkbox_changed(self, state):
        """复选框状态变化处理"""
        self.is_selected = (state == Qt.CheckState.Checked)
        self.update_card_style()
        # 更新批量按钮状态
        self._call_parent_method('update_batch_buttons_state')

    def set_status(self, status: str):
        """设置功能状态"""
        self.status = status
        self.status_label.setText(status)

        # 根据状态更新样式和按钮状态
        if status == "运行中":
            self.status_label.setStyleSheet(
                "color: white; font-size: 12px; padding: 2px 6px; border-radius: 4px; background-color: #28a745;")
            self.run_btn.setEnabled(False)
            self.pause_btn.setEnabled(True)
            self.pause_btn.setText("暂停")
            self.stop_btn.setEnabled(True)
        elif status == "暂停":
            self.status_label.setStyleSheet(
                "color: #212529; font-size: 12px; padding: 2px 6px; border-radius: 4px; background-color: #ffc107;")
            self.run_btn.setEnabled(True)
            self.pause_btn.setEnabled(True)
            self.pause_btn.setText("恢复")
            self.stop_btn.setEnabled(True)
        elif status == "错误":
            self.status_label.setStyleSheet(
                "color: white; font-size: 12px; padding: 2px 6px; border-radius: 4px; background-color: #dc3545;")
            self.run_btn.setEnabled(True)
            self.pause_btn.setEnabled(False)
            self.pause_btn.setText("暂停")
            self.stop_btn.setEnabled(False)
        else:  # 停止
            self.status_label.setStyleSheet(
                "color: #6c757d; font-size: 12px; padding: 2px 6px; border-radius: 4px; background-color: #f8f9fa;")
            self.run_btn.setEnabled(True)
            self.pause_btn.setEnabled(False)
            self.pause_btn.setText("暂停")
            self.stop_btn.setEnabled(False)

    def set_selected(self, selected: bool):
        """设置选中状态"""
        self.is_selected = selected
        self.checkbox.setChecked(selected)
        self.update_card_style()

    def _call_parent_method(self, method_name: str, *args):
        """安全调用父组件方法"""
        if self.parent and hasattr(self.parent, method_name):
            method = getattr(self.parent, method_name)
            if callable(method):
                method(*args)

    def on_pause_btn_clicked(self):
        """暂停按钮点击处理"""
        if self.parent and hasattr(self.parent, 'pause_feature'):
            self.parent.pause_feature(self.index)
            # 更新按钮文本
            if self.status == "运行中":
                self.pause_btn.setText("恢复")
            elif self.status == "暂停":
                self.pause_btn.setText("暂停") 


class GroupCard(QWidget):
    """分组卡片组件"""

    def __init__(self, group_name: str, features: List[tuple], parent=None):
        super().__init__(parent)
        self.group_name = group_name
        self.features = features  # [(index, feature), ...]
        self.parent = parent
        self.is_collapsed = False
        
        # UI组件
        self.header_widget: Optional[QWidget] = None
        self.content_widget: Optional[QWidget] = None
        self.toggle_button: Optional[QPushButton] = None
        self.group_label: Optional[QLabel] = None
        self.count_label: Optional[QLabel] = None
        self.feature_cards_layout: Optional[QVBoxLayout] = None
        
        self.init_ui()

    def init_ui(self):
        """初始化UI"""
        # 设置卡片样式
        self.setObjectName("groupCard")
        self.setStyleSheet("""
            QWidget#groupCard {
                background-color: white;
                border: 1px solid #e0e0e0;
                border-radius: 8px;
                margin: 8px 0px;
            }
            QWidget#groupCard:hover {
                border-color: #007bff;
                box-shadow: 0 2px 8px rgba(0, 123, 255, 0.15);
            }
        """)

        # 主布局
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # 创建头部（可点击）
        self.create_header()
        main_layout.addWidget(self.header_widget)

        # 创建内容区域
        self.create_content()
        main_layout.addWidget(self.content_widget)

    def create_header(self):
        """创建分组头部"""
        self.header_widget = QWidget()
        self.header_widget.setObjectName("groupHeader")
        self.header_widget.setStyleSheet("""
            QWidget#groupHeader {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #f8f9fa, stop:1 #e9ecef);
                border-bottom: 1px solid #dee2e6;
                border-radius: 8px 8px 0px 0px;
                padding: 12px;
            }
            QWidget#groupHeader:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #e3f2fd, stop:1 #bbdefb);
            }
        """)
        self.header_widget.setFixedHeight(60)
        self.header_widget.mousePressEvent = self.on_header_clicked

        header_layout = QHBoxLayout(self.header_widget)
        header_layout.setContentsMargins(12, 8, 12, 8)

        # 折叠/展开按钮
        self.toggle_button = QPushButton("▼")
        self.toggle_button.setObjectName("groupToggleBtn")
        self.toggle_button.setFixedSize(24, 24)
        self.toggle_button.setStyleSheet("""
            QPushButton#groupToggleBtn {
                background-color: transparent;
                border: none;
                color: #495057;
                font-size: 12px;
                font-weight: bold;
                border-radius: 12px;
            }
            QPushButton#groupToggleBtn:hover {
                background-color: #007bff;
                color: white;
            }
        """)
        self.toggle_button.clicked.connect(self.toggle_collapse)
        header_layout.addWidget(self.toggle_button)

        # 分组图标和名称
        icon_label = QLabel("📁")
        icon_label.setStyleSheet("font-size: 18px; margin-right: 8px;")
        header_layout.addWidget(icon_label)

        self.group_label = QLabel(self.group_name)
        self.group_label.setStyleSheet("""
            font-size: 16px;
            font-weight: bold;
            color: #212529;
        """)
        header_layout.addWidget(self.group_label)

        header_layout.addStretch()

        # 功能数量
        self.count_label = QLabel(f"{len(self.features)} 个功能")
        self.count_label.setStyleSheet("""
            color: #6c757d;
            font-size: 12px;
            padding: 4px 8px;
            background-color: #e9ecef;
            border-radius: 12px;
        """)
        header_layout.addWidget(self.count_label)

    def create_content(self):
        """创建内容区域"""
        self.content_widget = QWidget()
        self.content_widget.setObjectName("groupContent")
        self.content_widget.setStyleSheet("""
            QWidget#groupContent {
                background-color: #fafafa;
                border-radius: 0px 0px 8px 8px;
                padding: 8px;
            }
        """)

        # 内容布局
        content_layout = QVBoxLayout(self.content_widget)
        content_layout.setContentsMargins(8, 8, 8, 8)
        content_layout.setSpacing(6)

        # 功能卡片容器
        self.feature_cards_layout = QVBoxLayout()
        self.feature_cards_layout.setSpacing(4)

        # 添加功能卡片
        for index, feature in self.features:
            card = FeatureCard(feature, index, self.parent)
            self.feature_cards_layout.addWidget(card)

        content_layout.addLayout(self.feature_cards_layout)

    def toggle_collapse(self):
        """切换折叠/展开状态"""
        self.is_collapsed = not self.is_collapsed
        
        if self.is_collapsed:
            self.content_widget.hide()
            self.toggle_button.setText("▶")
            self.header_widget.setStyleSheet("""
                QWidget#groupHeader {
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                        stop:0 #f8f9fa, stop:1 #e9ecef);
                    border: 1px solid #dee2e6;
                    border-radius: 8px;
                    padding: 12px;
                }
                QWidget#groupHeader:hover {
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                        stop:0 #e3f2fd, stop:1 #bbdefb);
                }
            """)
        else:
            self.content_widget.show()
            self.toggle_button.setText("▼")
            self.header_widget.setStyleSheet("""
                QWidget#groupHeader {
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                        stop:0 #f8f9fa, stop:1 #e9ecef);
                    border-bottom: 1px solid #dee2e6;
                    border-radius: 8px 8px 0px 0px;
                    padding: 12px;
                }
                QWidget#groupHeader:hover {
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                        stop:0 #e3f2fd, stop:1 #bbdefb);
                }
            """)

    def on_header_clicked(self, event):
        """头部点击事件"""
        self.toggle_collapse()

    def set_visible(self, visible: bool):
        """设置整个分组卡片的可见性"""
        self.setVisible(visible)

    def get_feature_cards(self) -> List['FeatureCard']:
        """获取所有功能卡片"""
        cards = []
        for i in range(self.feature_cards_layout.count()):
            item = self.feature_cards_layout.itemAt(i)
            if item and item.widget():
                cards.append(item.widget())
        return cards 