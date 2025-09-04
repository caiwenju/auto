#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from typing import List, Optional
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel,
    QPushButton, QLineEdit, QComboBox, QDoubleSpinBox, QSpinBox,
    QListWidget, QApplication
)
from PySide6.QtCore import Qt

from automation import AutomationStep, AutomationFeature
from ui_components import StepListWidget


class FeatureDialog(QDialog):
    """功能编辑对话框"""

    def __init__(self, parent=None, feature: AutomationFeature = None):
        super().__init__(parent)
        self.feature: AutomationFeature = feature
        self.steps: List[AutomationStep] = (
            feature.steps.copy() if feature else [])

        # UI组件
        self.name_edit: Optional[QLineEdit] = None
        self.group_combo: Optional[QComboBox] = None  # 添加分组选择框
        self.steps_list: Optional[StepListWidget] = None
        self.ok_button: Optional[QPushButton] = None
        self.cancel_button: Optional[QPushButton] = None

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

        # 功能分组
        group_layout = QHBoxLayout()
        group_layout.addWidget(QLabel("功能分组:"))
        self.group_combo = QComboBox()
        self.group_combo.setFixedHeight(32)
        self.group_combo.setEditable(True)
        self.group_combo.setPlaceholderText("输入或选择分组")
        
        # 添加默认分组选项
        self.group_combo.addItem("默认")
        
        # 添加现有的分组选项（如果父窗口有 feature_manager）
        if hasattr(self.parent(), 'feature_manager'):
            existing_groups = self.parent().feature_manager.get_all_groups()
            for group in existing_groups:
                if group != "默认" and self.group_combo.findText(group) == -1:
                    self.group_combo.addItem(group)
        
        # 如果有现有功能，设置其分组
        if self.feature and hasattr(self.feature, 'group'):
            current_group = self.feature.group
            if current_group != "默认":
                # 如果当前分组不在列表中，添加它
                if self.group_combo.findText(current_group) == -1:
                    self.group_combo.addItem(current_group)
            self.group_combo.setCurrentText(current_group)
        else:
            self.group_combo.setCurrentText("默认")
            
        group_layout.addWidget(self.group_combo)
        layout.addLayout(group_layout)

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
            steps=self.steps,
            group=self.group_combo.currentText()
        )


class StepEditDialog(QDialog):
    """步骤编辑对话框"""

    def __init__(
            self,
            x: float,
            y: float,
            parent=None,
            step: AutomationStep = None):
        super().__init__(parent)
        self.step: AutomationStep = step
        self.x: float = x
        self.y: float = y

        # UI组件
        self.name_edit: Optional[QLineEdit] = None  # 添加名称编辑框
        self.x_spinbox: Optional[QDoubleSpinBox] = None
        self.y_spinbox: Optional[QDoubleSpinBox] = None
        self.action_combo: Optional[QComboBox] = None
        self.delay_spinbox: Optional[QDoubleSpinBox] = None
        self.text_edit: Optional[QLineEdit] = None
        self.ok_button: Optional[QPushButton] = None
        self.cancel_button: Optional[QPushButton] = None

        # 设置窗口标志，确保始终置顶且模态
        self.setWindowFlags(
            Qt.WindowType.Dialog |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.MSWindowsFixedSizeDialogHint
        )

        # 设置窗口属性
        self.setWindowTitle("编辑步骤")
        self.setModal(True)
        self.resize(400, 320)  # 增加高度以容纳名称输入框

        # 创建UI
        self.init_ui()

    def init_ui(self):
        """初始化对话框UI"""
        # 创建主布局
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        layout.setContentsMargins(15, 15, 15, 15)

        # 步骤名称
        name_layout = QHBoxLayout()
        name_layout.addWidget(QLabel("步骤名称:"))
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("请输入步骤名称（可选）")
        if self.step and self.step.name:
            self.name_edit.setText(self.step.name)
        name_layout.addWidget(self.name_edit)
        layout.addLayout(name_layout)

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
        self.action_combo.addItems(
            ["左键单击", "右键单击", "双击", "左键多击", "右键多击", "输入文本"])
        if self.step:
            index = self.action_combo.findText(self.step.action)
            if index >= 0:
                self.action_combo.setCurrentIndex(index)
        action_layout.addWidget(self.action_combo)
        layout.addLayout(action_layout)

        # 多击次数设置
        click_count_layout = QHBoxLayout()
        click_count_layout.addWidget(QLabel("点击次数:"))
        self.click_count_spinbox = QSpinBox()
        self.click_count_spinbox.setRange(1, 99999)  # 限制最大值避免内存问题
        self.click_count_spinbox.setValue(
            self.step.click_count if self.step and hasattr(
                self.step, 'click_count') else 1)  # 默认1次
        self.click_count_spinbox.setSuffix(" 次")
        self.click_count_spinbox.setToolTip("设置多击的点击次数（无限制）")
        click_count_layout.addWidget(self.click_count_spinbox)

        # 点击间隔设置
        click_count_layout.addWidget(QLabel("点击间隔:"))
        self.click_interval_spinbox = QDoubleSpinBox()
        self.click_interval_spinbox.setRange(0.001, 60.0)  # 1ms到60秒，避免过长间隔
        self.click_interval_spinbox.setSingleStep(0.01)
        self.click_interval_spinbox.setValue(
            self.step.click_interval if self.step and hasattr(
                self.step, 'click_interval') else 0.05)  # 默认50ms
        self.click_interval_spinbox.setSuffix(" 秒")
        self.click_interval_spinbox.setToolTip("设置每次点击之间的间隔时间（0.001-60秒）")
        click_count_layout.addWidget(self.click_interval_spinbox)

        click_count_layout.addStretch()
        layout.addLayout(click_count_layout)

        # 延迟设置
        delay_layout = QHBoxLayout()
        delay_layout.addWidget(QLabel("延迟(秒):"))
        self.delay_spinbox = QDoubleSpinBox()
        self.delay_spinbox.setRange(0.0, 60.0)  # 最大延迟60秒，避免过长延迟
        self.delay_spinbox.setSingleStep(0.1)
        self.delay_spinbox.setValue(self.step.delay if self.step else 0.0)
        delay_layout.addWidget(self.delay_spinbox)
        layout.addLayout(delay_layout)

        # 文本输入
        text_layout = QHBoxLayout()
        text_layout.addWidget(QLabel("文本:"))
        self.text_edit = QLineEdit()
        self.text_edit.setText(self.step.text if self.step else "")
        self.text_edit.setPlaceholderText("输入要发送的文本")
        self.text_edit.setToolTip("输入要发送到目标窗口的文本内容")
        text_layout.addWidget(self.text_edit)
        layout.addLayout(text_layout)

        # 连接动作选择变化信号
        self.action_combo.currentTextChanged.connect(self.on_action_changed)

        # 初始化文本输入框的显示状态
        self.on_action_changed(self.action_combo.currentText())

        # 按钮
        button_layout = QHBoxLayout()
        self.ok_button = QPushButton("确定")
        self.ok_button.clicked.connect(self.accept)
        self.cancel_button = QPushButton("取消")
        self.cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(self.ok_button)
        button_layout.addWidget(self.cancel_button)
        layout.addLayout(button_layout)

    def on_action_changed(self, action: str):
        """动作选择变化处理"""
        # 根据动作类型显示/隐藏相关控件
        if action == "输入文本":
            self.text_edit.setVisible(True)
            self.text_edit.setEnabled(True)
            self.click_count_spinbox.setVisible(False)
            self.click_interval_spinbox.setVisible(False)
        elif action in ["左键多击", "右键多击"]:
            self.text_edit.setVisible(False)
            self.text_edit.setEnabled(False)
            self.click_count_spinbox.setVisible(True)
            self.click_interval_spinbox.setVisible(True)
        else:
            self.text_edit.setVisible(False)
            self.text_edit.setEnabled(False)
            self.click_count_spinbox.setVisible(False)
            self.click_interval_spinbox.setVisible(False)

    def get_step(self) -> AutomationStep:
        """获取编辑后的步骤"""
        # 生成默认步骤名称（如果用户未输入）
        name = self.name_edit.text().strip()
        if not name:
            action = self.action_combo.currentText()
            x_percent = self.x_spinbox.value()
            y_percent = self.y_spinbox.value()
            name = f"{action} ({x_percent:.1f}%, {y_percent:.1f}%)"
            
        return AutomationStep(
            x=self.x_spinbox.value() / 100.0,  # 转换回0-1范围
            y=self.y_spinbox.value() / 100.0,  # 转换回0-1范围
            action=self.action_combo.currentText(),
            delay=self.delay_spinbox.value(),
            text=self.text_edit.text(),
            click_count=self.click_count_spinbox.value(),
            click_interval=self.click_interval_spinbox.value(),
            name=name
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