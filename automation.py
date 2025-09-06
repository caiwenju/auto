#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import time
import json
import os
import sys
from typing import List, Dict, Optional
import win32api
import win32con
import win32gui
import win32clipboard
from PySide6.QtCore import QThread, Signal

from window_manager import WindowManager


def get_resource_path(relative_path):
    """获取资源文件的绝对路径，支持开发环境和打包环境"""
    try:
        # PyInstaller会创建临时文件夹并存储路径在_MEIPASS中
        base_path = sys._MEIPASS
    except Exception:
        # 开发环境，使用脚本所在目录
        base_path = os.path.abspath(".")
    
    return os.path.join(base_path, relative_path)

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


class FeatureGroup:
    """功能分组类"""

    def __init__(self, group_name: str, features: List[AutomationFeature] = None):
        self.group_name: str = group_name
        self.features: List[AutomationFeature] = features or []

    def to_dict(self) -> Dict:
        """转换为字典"""
        return {
            'group_name': self.group_name,
            'features': [feature.to_dict() for feature in self.features]
        }

    @classmethod
    def from_dict(cls, data: Dict) -> 'FeatureGroup':
        """从字典创建实例"""
        return cls(
            group_name=data['group_name'],
            features=[AutomationFeature.from_dict(feature) for feature in data.get('features', [])]
        )

    def add_feature(self, feature: AutomationFeature):
        """添加功能到分组"""
        self.features.append(feature)

    def remove_feature(self, index: int) -> Optional[AutomationFeature]:
        """从分组中移除功能"""
        if 0 <= index < len(self.features):
            return self.features.pop(index)
        return None

    def get_feature_count(self) -> int:
        """获取功能数量"""
        return len(self.features)


class FeatureManager:
    """功能管理器"""

    def __init__(self):
        self.groups: List[FeatureGroup] = []
        # 读取时使用资源路径（支持打包后的环境）
        self.read_file = get_resource_path("automation_features.json")
        # 保存时使用当前目录（开发环境可以保存，打包后保存到exe目录）
        self.data_file = "automation_features.json"
        self.load_features()

    def load_features(self):
        """加载功能列表"""
        try:
            data = None
            # 优先尝试从当前目录读取（开发环境或用户自定义的数据）
            if os.path.exists(self.data_file):
                with open(self.data_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
            # 如果当前目录没有，尝试从打包的资源中读取
            elif os.path.exists(self.read_file):
                with open(self.read_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
            
            if data:
                self._parse_data(data)
            else:
                # 创建默认分组
                self.groups = [FeatureGroup("默认")]
                
        except Exception as e:
            print(f"加载功能列表失败: {e}")
            # 创建默认分组
            self.groups = [FeatureGroup("默认")]

    def _parse_data(self, data: Dict):
        """解析数据，支持新旧格式"""
        if 'groups' in data:
            # 新格式：以分组为主的结构
            self.groups = [FeatureGroup.from_dict(group_data) for group_data in data['groups']]
        elif 'features' in data:
            # 中间格式：features + empty_groups
            self._migrate_from_features_format(data)
        else:
            # 旧格式：纯features列表
            self._migrate_from_old_format(data)

    def _migrate_from_features_format(self, data: Dict):
        """从features+empty_groups格式迁移"""
        groups_dict = {}
        
        # 处理有功能的分组
        for feature_data in data.get('features', []):
            feature = AutomationFeature.from_dict(feature_data)
            group_name = feature_data.get('group', '默认')
            
            if group_name not in groups_dict:
                groups_dict[group_name] = FeatureGroup(group_name)
            groups_dict[group_name].add_feature(feature)
        
        # 处理空分组
        for empty_group in data.get('empty_groups', []):
            if empty_group not in groups_dict:
                groups_dict[empty_group] = FeatureGroup(empty_group)
        
        # 确保有默认分组
        if '默认' not in groups_dict:
            groups_dict['默认'] = FeatureGroup('默认')
        
        self.groups = list(groups_dict.values())

    def _migrate_from_old_format(self, data: List):
        """从旧的纯features列表格式迁移"""
        groups_dict = {}
        
        for feature_data in data:
            feature = AutomationFeature.from_dict(feature_data)
            group_name = feature_data.get('group', '默认')
            
            if group_name not in groups_dict:
                groups_dict[group_name] = FeatureGroup(group_name)
            groups_dict[group_name].add_feature(feature)
        
        # 确保有默认分组
        if '默认' not in groups_dict:
            groups_dict['默认'] = FeatureGroup('默认')
        
        self.groups = list(groups_dict.values())

    def save_features(self):
        """保存功能列表"""
        try:
            data = {
                'groups': [group.to_dict() for group in self.groups]
            }
            with open(self.data_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"保存功能列表失败: {e}")

    def add_feature_to_group(self, feature: AutomationFeature, group_name: str):
        """添加功能到指定分组"""
        group = self.get_or_create_group(group_name)
        group.add_feature(feature)
        self.save_features()

    def get_or_create_group(self, group_name: str) -> FeatureGroup:
        """获取或创建分组"""
        for group in self.groups:
            if group.group_name == group_name:
                return group
        
        # 创建新分组
        new_group = FeatureGroup(group_name)
        self.groups.append(new_group)
        return new_group

    def get_feature_by_global_index(self, global_index: int) -> tuple[FeatureGroup, int, AutomationFeature]:
        """通过全局索引获取功能"""
        current_index = 0
        for group in self.groups:
            for local_index, feature in enumerate(group.features):
                if current_index == global_index:
                    return group, local_index, feature
                current_index += 1
        raise IndexError(f"功能索引 {global_index} 超出范围")

    def update_feature(self, global_index: int, updated_feature: AutomationFeature, new_group_name: str = None):
        """更新功能"""
        try:
            old_group, local_index, old_feature = self.get_feature_by_global_index(global_index)
            
            if new_group_name and new_group_name != old_group.group_name:
                # 移动到新分组
                old_group.remove_feature(local_index)
                new_group = self.get_or_create_group(new_group_name)
                new_group.add_feature(updated_feature)
            else:
                # 在同一分组内更新
                old_group.features[local_index] = updated_feature
            
            self.save_features()
        except IndexError as e:
            print(f"更新功能失败: {e}")

    def delete_feature(self, global_index: int):
        """删除功能"""
        try:
            group, local_index, feature = self.get_feature_by_global_index(global_index)
            group.remove_feature(local_index)
            self.save_features()
        except IndexError as e:
            print(f"删除功能失败: {e}")

    def move_feature(self, global_index: int, target_group_name: str):
        """将功能移动到目标分组"""
        try:
            source_group, local_index, feature = self.get_feature_by_global_index(global_index)
            
            if source_group.group_name != target_group_name:
                # 从源分组移除
                source_group.remove_feature(local_index)
                
                # 添加到目标分组
                target_group = self.get_or_create_group(target_group_name)
                target_group.add_feature(feature)
                
                self.save_features()
        except IndexError as e:
            print(f"移动功能失败: {e}") 

    def get_all_groups(self) -> List[str]:
        """获取所有可用的分组"""
        return sorted([group.group_name for group in self.groups])

    def get_group(self, group_name: str) -> Optional[FeatureGroup]:
        """根据分组名获取分组"""
        for group in self.groups:
            if group.group_name == group_name:
                return group
        return None

    def get_features_by_group(self, group_name: str) -> List[AutomationFeature]:
        """根据分组获取功能列表"""
        group = self.get_group(group_name)
        return group.features if group else []
    
    def add_empty_group(self, group_name: str):
        """添加空分组"""
        if group_name and not self.get_group(group_name):
            new_group = FeatureGroup(group_name)
            self.groups.append(new_group)
            self.save_features()
    
    def remove_group(self, group_name: str):
        """移除分组（只有在分组为空时才能移除）"""
        group = self.get_group(group_name)
        if group and len(group.features) == 0 and group_name != '默认':
            self.groups.remove(group)
            self.save_features()

    def delete_group(self, group_name: str) -> bool:
        """删除分组（强制删除，不管是否为空）"""
        if group_name == '默认':
            return False  # 不允许删除默认分组
        
        group = self.get_group(group_name)
        if group:
            self.groups.remove(group)
            self.save_features()
            return True
        return False

    def rename_group(self, old_name: str, new_name: str) -> bool:
        """重命名分组"""
        if old_name == '默认':
            return False  # 不允许重命名默认分组
        
        group = self.get_group(old_name)
        if group and not self.get_group(new_name):
            group.group_name = new_name
            self.save_features()
            return True
        return False

    def get_all_features(self) -> List[AutomationFeature]:
        """获取所有功能的扁平列表（用于向后兼容）"""
        all_features = []
        for group in self.groups:
            all_features.extend(group.features)
        return all_features

    def get_total_feature_count(self) -> int:
        """获取总功能数量"""
        return sum(len(group.features) for group in self.groups)

    @property
    def features(self) -> List[AutomationFeature]:
        """向后兼容属性：返回所有功能的扁平列表"""
        return self.get_all_features() 