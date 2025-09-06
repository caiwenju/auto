#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
安全工具模块
提供反调试、反编译保护功能
"""

import os
import sys
import time
import threading
import ctypes
from ctypes import wintypes
import hashlib
import psutil

class SecurityChecker:
    """安全检查器"""
    
    def __init__(self):
        self.is_debugging = False
        self.protection_enabled = True
        self._start_monitoring()
    
    def _start_monitoring(self):
        """启动监控线程"""
        if self.protection_enabled:
            monitor_thread = threading.Thread(target=self._security_monitor, daemon=True)
            monitor_thread.start()
    
    def _security_monitor(self):
        """安全监控主循环"""
        while self.protection_enabled:
            try:
                # 检查调试器
                if self._check_debugger():
                    self._handle_security_violation("检测到调试器")
                
                # 检查虚拟机
                if self._check_vm_environment():
                    self._handle_security_violation("检测到虚拟机环境")
                
                # 检查可疑进程
                if self._check_suspicious_processes():
                    self._handle_security_violation("检测到可疑进程")
                
                time.sleep(5)  # 每5秒检查一次
                
            except Exception as e:
                # 静默处理异常，避免暴露安全机制
                pass
    
    def _check_debugger(self) -> bool:
        """检查是否有调试器附加"""
        try:
            # 方法1: 使用Windows API检查
            kernel32 = ctypes.windll.kernel32
            if kernel32.IsDebuggerPresent():
                return True
            
            # 方法2: 检查调试标志
            if hasattr(sys, 'gettrace') and sys.gettrace() is not None:
                return True
            
            # 方法3: 时间差检查
            start_time = time.time()
            time.sleep(0.01)
            if time.time() - start_time > 0.05:  # 如果延迟过大，可能被调试
                return True
                
        except Exception:
            pass
        
        return False
    
    def _check_vm_environment(self) -> bool:
        """检查是否在虚拟机环境中运行"""
        try:
            # 检查常见的虚拟机标识
            vm_indicators = [
                'vmware', 'virtualbox', 'vbox', 'qemu', 
                'xen', 'hyper-v', 'parallels'
            ]
            
            # 检查进程名
            for proc in psutil.process_iter(['name']):
                try:
                    proc_name = proc.info['name'].lower()
                    for indicator in vm_indicators:
                        if indicator in proc_name:
                            return True
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
            
            # 检查注册表中的虚拟机标识（Windows）
            try:
                import winreg
                key_paths = [
                    r"SYSTEM\CurrentControlSet\Services\VBoxService",
                    r"SYSTEM\CurrentControlSet\Services\VMTools",
                    r"SOFTWARE\VMware, Inc.\VMware Tools"
                ]
                
                for key_path in key_paths:
                    try:
                        winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, key_path)
                        return True
                    except FileNotFoundError:
                        continue
            except ImportError:
                pass
                
        except Exception:
            pass
        
        return False
    
    def _check_suspicious_processes(self) -> bool:
        """检查可疑进程"""
        try:
            suspicious_processes = [
                'ollydbg', 'x64dbg', 'x32dbg', 'windbg', 'ida', 'ida64',
                'cheatengine', 'processhacker', 'procexp', 'procmon',
                'wireshark', 'fiddler', 'charles', 'burpsuite',
                'dnspy', 'reflexil', 'de4dot', 'ilspy'
            ]
            
            for proc in psutil.process_iter(['name']):
                try:
                    proc_name = proc.info['name'].lower()
                    for suspicious in suspicious_processes:
                        if suspicious in proc_name:
                            return True
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
                    
        except Exception:
            pass
        
        return False
    
    def _handle_security_violation(self, reason: str):
        """处理安全违规"""
        try:
            # 记录违规（可选）
            # print(f"安全违规: {reason}")
            
            # 执行保护措施
            self._execute_protection()
            
        except Exception:
            pass
    
    def _execute_protection(self):
        """执行保护措施"""
        try:
            # 方法1: 优雅退出
            os._exit(1)
            
        except Exception:
            try:
                # 方法2: 强制退出
                sys.exit(1)
            except Exception:
                pass
    
    def verify_integrity(self) -> bool:
        """验证程序完整性"""
        try:
            # 获取当前执行文件的路径
            if getattr(sys, 'frozen', False):
                # 打包后的exe文件
                exe_path = sys.executable
            else:
                # 开发环境
                return True
            
            # 计算文件哈希
            with open(exe_path, 'rb') as f:
                file_hash = hashlib.sha256(f.read()).hexdigest()
            
            # 这里可以预设一个期望的哈希值进行比较
            # 为了演示，这里总是返回True
            return True
            
        except Exception:
            return False
    
    def disable_protection(self):
        """禁用保护（仅用于调试）"""
        self.protection_enabled = False


# 全局安全检查器实例
_security_checker = None

def init_security():
    """初始化安全检查"""
    global _security_checker
    if _security_checker is None:
        _security_checker = SecurityChecker()
    return _security_checker

def check_security():
    """执行安全检查"""
    checker = init_security()
    return checker.verify_integrity()

def disable_security():
    """禁用安全检查（仅用于调试）"""
    global _security_checker
    if _security_checker:
        _security_checker.disable_protection()

# 自动初始化
if __name__ != "__main__":
    # 只有在被导入时才启动安全检查
    init_security() 