#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import time
import json
import os
from typing import List, Dict, Optional
import win32api
import win32con
import win32gui
import win32clipboard
from PySide6.QtCore import QThread, Signal

from window_manager import WindowManager


class AutomationStep:
    """自动化步骤类"""

    def __init__(
            self,
            x: float = 0.0,
            y: float = 0.0,
            action: str = "左键单击",
            delay: float = 0.0,
            text: str = "",
            click_count: int = 1,
            click_interval: float = 0.05,
            name: str = ""):
        self.x: float = x  # 相对坐标（百分比）
        self.y: float = y  # 相对坐标（百分比）
        self.action: str = action
        self.delay: float = delay
        self.text: str = text
        self.click_count: int = click_count  # 点击次数
        self.click_interval: float = click_interval  # 点击间隔（秒）
        self.name: str = name  # 步骤名称

    def to_dict(self) -> Dict:
        """转换为字典"""
        return {
            'x': self.x,
            'y': self.y,
            'action': self.action,
            'delay': self.delay,
            'text': self.text,
            'click_count': self.click_count,
            'click_interval': self.click_interval,
            'name': self.name
        }

    @classmethod
    def from_dict(cls, data: Dict) -> 'AutomationStep':
        """从字典创建实例"""
        # 处理旧版本的"多击"动作，转换为"左键多击"
        action = data.get('action', '左键单击')
        if action == "多击":
            action = "左键多击"

        return cls(
            x=float(data.get('x', 0.0)),
            y=float(data.get('y', 0.0)),
            action=action,
            delay=float(data.get('delay', 0.0)),
            text=data.get('text', ''),
            click_count=int(data.get('click_count', 1)),
            click_interval=float(data.get('click_interval', 0.05)),
            name=data.get('name', '')
        )


class AutomationExecutor(QThread):
    """自动化执行器"""

    step_completed = Signal(int, str)  # 步骤完成信号
    execution_finished = Signal(bool, str)  # 执行完成信号
    progress_updated = Signal(int)  # 进度更新信号

    def __init__(
            self,
            steps: List[AutomationStep],
            window_manager: WindowManager,
            feature_index: int = -1):
        super().__init__()
        
        self.steps: List[AutomationStep] = steps
        self.window_manager: WindowManager = window_manager
        self.feature_index: int = feature_index
        self.running: bool = False
        self.paused: bool = False

    def run(self):
        """执行自动化步骤 - 单次完整执行"""
        try:
            print("[EXECUTOR] 开始执行功能（最小单元）")
            self.running = True
            self.paused = False
            print(f"[EXECUTOR] 总步骤数: {len(self.steps)}")

            for i, step in enumerate(self.steps):
                print(f"[EXECUTOR] 执行步骤 {i + 1}/{len(self.steps)}: {step.action}")
                
                if not self.running:
                    print("[EXECUTOR] 执行被停止")
                    break

                # 等待暂停状态结束
                while self.paused and self.running:
                    print("[EXECUTOR] 执行被暂停")
                    time.sleep(0.1)

                if not self.running:
                    print("[EXECUTOR] 执行被停止")
                    break

                # 检查窗口是否仍然有效
                if not self.window_manager.is_window_active():
                    print("[EXECUTOR] 目标窗口已关闭或失效")
                    self.execution_finished.emit(False, "目标窗口已关闭或失效")
                    return

                # 执行步骤
                success = self._execute_step(step)
                if success:
                    print(f"[EXECUTOR] 步骤 {i + 1} 执行成功")
                    self.step_completed.emit(i + 1, f"步骤 {i + 1} 执行成功")
                else:
                    print(f"[EXECUTOR] 步骤 {i + 1} 执行失败")
                    self.step_completed.emit(i + 1, f"步骤 {i + 1} 执行失败")
                    self.execution_finished.emit(False, f"步骤 {i + 1} 执行失败")
                    return

                # 更新进度
                progress = int((i + 1) / len(self.steps) * 100)
                self.progress_updated.emit(progress)

                # 延迟
                if step.delay > 0:
                    time.sleep(step.delay)

            if self.running:
                print("[EXECUTOR] 单次功能执行完成")
                self.execution_finished.emit(True, "单次功能执行完成")
            else:
                print("[EXECUTOR] 执行被用户停止")
                self.execution_finished.emit(False, "执行被用户停止")

        except Exception as e:
            print(f"[EXECUTOR] 执行器运行错误: {e}")
            import traceback
            traceback.print_exc()
            self.execution_finished.emit(False, f"执行出错: {str(e)}")
        finally:
            print("[EXECUTOR] 最小单元执行完成，线程即将结束")
            self.running = False

    def _execute_step(self, step: AutomationStep) -> bool:
        """执行单个步骤"""
        try:
            # 检查窗口是否仍然有效
            try:
                if not self.window_manager.is_window_active():
                    print("目标窗口已失效")
                    return False
            except Exception as e:
                print(f"检查窗口状态失败: {e}")
                return False

            # 获取屏幕坐标
            try:
                screen_x, screen_y = self.window_manager.get_screen_coordinates(
                    step.x, step.y)
            except Exception as e:
                print(f"获取屏幕坐标失败: {e}")
                return False

            # 移动鼠标到目标位置
            try:
                print(f"移动鼠标到: ({screen_x}, {screen_y})")
                win32api.SetCursorPos((int(screen_x), int(screen_y)))
                time.sleep(0.1)  # 短暂延迟确保鼠标移动到位
            except Exception as e:
                print(f"移动鼠标失败: {e}")
                import traceback
                traceback.print_exc()
                return False

            # 执行相应的动作
            if step.action == "左键单击":
                try:
                    print(f"执行左键单击: ({screen_x}, {screen_y})")
                    # 确保参数为整数
                    x, y = int(screen_x), int(screen_y)
                    win32api.mouse_event(
                        win32con.MOUSEEVENTF_LEFTDOWN, x, y, 0, 0)
                    win32api.mouse_event(
                        win32con.MOUSEEVENTF_LEFTUP, x, y, 0, 0)
                except Exception as e:
                    print(f"左键单击失败: {e}")
                    import traceback
                    traceback.print_exc()
                    return False
            elif step.action == "右键单击":
                try:
                    print(f"执行右键单击: ({screen_x}, {screen_y})")
                    # 确保参数为整数
                    x, y = int(screen_x), int(screen_y)
                    win32api.mouse_event(
                        win32con.MOUSEEVENTF_RIGHTDOWN, x, y, 0, 0)
                    win32api.mouse_event(
                        win32con.MOUSEEVENTF_RIGHTUP, x, y, 0, 0)
                except Exception as e:
                    print(f"右键单击失败: {e}")
                    import traceback
                    traceback.print_exc()
                    return False
            elif step.action == "双击":
                try:
                    print(f"执行双击: ({screen_x}, {screen_y})")
                    # 确保参数为整数
                    x, y = int(screen_x), int(screen_y)
                    win32api.mouse_event(
                        win32con.MOUSEEVENTF_LEFTDOWN, x, y, 0, 0)
                    win32api.mouse_event(
                        win32con.MOUSEEVENTF_LEFTUP, x, y, 0, 0)
                    time.sleep(0.05)
                    win32api.mouse_event(
                        win32con.MOUSEEVENTF_LEFTDOWN, x, y, 0, 0)
                    win32api.mouse_event(
                        win32con.MOUSEEVENTF_LEFTUP, x, y, 0, 0)
                except Exception as e:
                    print(f"双击失败: {e}")
                    import traceback
                    traceback.print_exc()
                    return False
            elif step.action == "左键多击":
                try:
                    # 执行多次左键点击
                    click_count = getattr(step, 'click_count', 1)  # 默认1次
                    click_interval = getattr(
                        step, 'click_interval', 0.05)  # 默认50ms
                    print(f"执行左键多击: ({screen_x}, {screen_y}), 次数: {click_count}, 间隔: {click_interval}秒")
                    # 确保参数为整数
                    x, y = int(screen_x), int(screen_y)
                    for i in range(click_count):
                        win32api.mouse_event(
                            win32con.MOUSEEVENTF_LEFTDOWN, x, y, 0, 0)
                        win32api.mouse_event(
                            win32con.MOUSEEVENTF_LEFTUP, x, y, 0, 0)
                        if i < click_count - 1:  # 不是最后一次点击
                            time.sleep(click_interval)  # 使用自定义间隔
                except Exception as e:
                    print(f"左键多击失败: {e}")
                    import traceback
                    traceback.print_exc()
                    return False
            elif step.action == "右键多击":
                try:
                    # 执行多次右键点击
                    click_count = getattr(step, 'click_count', 1)  # 默认1次
                    click_interval = getattr(
                        step, 'click_interval', 0.05)  # 默认50ms
                    print(f"执行右键多击: ({screen_x}, {screen_y}), 次数: {click_count}, 间隔: {click_interval}秒")
                    # 确保参数为整数
                    x, y = int(screen_x), int(screen_y)
                    for i in range(click_count):
                        win32api.mouse_event(
                            win32con.MOUSEEVENTF_RIGHTDOWN, x, y, 0, 0)
                        win32api.mouse_event(
                            win32con.MOUSEEVENTF_RIGHTUP, x, y, 0, 0)
                        if i < click_count - 1:  # 不是最后一次点击
                            time.sleep(click_interval)  # 使用自定义间隔
                except Exception as e:
                    print(f"右键多击失败: {e}")
                    import traceback
                    traceback.print_exc()
                    return False
            elif step.action == "输入文本" and step.text:
                # 实现文本输入功能
                try:
                    # 验证文本内容
                    if not step.text.strip():
                        print("文本内容为空，跳过输入")
                        return True

                    # 确保目标窗口处于活动状态
                    if self.window_manager.window_handle:
                        win32gui.SetForegroundWindow(
                            self.window_manager.window_handle)
                        time.sleep(0.1)  # 等待窗口激活

                    # 方法1：使用剪贴板粘贴（推荐）
                    try:
                        # 将文本复制到剪贴板
                        win32clipboard.OpenClipboard()
                        try:
                            win32clipboard.EmptyClipboard()
                            win32clipboard.SetClipboardText(
                                step.text, win32clipboard.CF_UNICODETEXT)
                        finally:
                            win32clipboard.CloseClipboard()

                        # 发送 Ctrl+V 粘贴文本
                        win32api.keybd_event(
                            win32con.VK_CONTROL, 0, 0, 0)  # Ctrl 按下
                        win32api.keybd_event(ord('V'), 0, 0, 0)  # V 按下
                        win32api.keybd_event(
                            ord('V'), 0, win32con.KEYEVENTF_KEYUP, 0)  # V 释放
                        win32api.keybd_event(
                            win32con.VK_CONTROL, 0, win32con.KEYEVENTF_KEYUP, 0)  # Ctrl 释放

                        time.sleep(0.1)  # 等待粘贴完成

                    except Exception as clipboard_error:
                        print(f"剪贴板方法失败，尝试直接输入: {clipboard_error}")

                        # 方法2：直接输入字符（备选方案）
                        for char in step.text:
                            # 获取字符的虚拟键码
                            vk_code = win32api.VkKeyScan(char)
                            if vk_code != -1:
                                # 发送按键
                                win32api.keybd_event(
                                    vk_code & 0xFF, 0, 0, 0)  # 按下
                                win32api.keybd_event(
                                    vk_code & 0xFF, 0, win32con.KEYEVENTF_KEYUP, 0)  # 释放
                                time.sleep(0.01)  # 字符间短暂延迟

                except Exception as e:
                    print(f"文本输入失败: {e}")
                    return False

            return True

        except Exception as e:
            print(f"执行步骤失败: {e}")
            import traceback
            traceback.print_exc()
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
        self.name: str = name
        self.steps: List[AutomationStep] = steps

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
                    self.features = [
                        AutomationFeature.from_dict(feature) for feature in data]
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