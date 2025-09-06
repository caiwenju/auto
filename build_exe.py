#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
自动化工具打包脚本 - 简洁版
适用于JSON数据已内嵌在client.py的情况
"""

import os
import sys
import shutil
import subprocess
from pathlib import Path

def check_environment():
    """检查打包环境"""
    print("正在检查打包环境...")
    
    # 检查必要文件
    required_files = ['client.py']
    missing_files = []
    for file in required_files:
        if not Path(file).exists():
            missing_files.append(file)
    
    if missing_files:
        print(f"✗ 缺少必要文件: {', '.join(missing_files)}")
        return False
    
    # 检查图标文件（可选）
    icon_files = ['C.ico', 'R.ico']
    available_icons = [f for f in icon_files if Path(f).exists()]
    if available_icons:
        print(f"✓ 找到图标文件: {', '.join(available_icons)}")
    else:
        print("⚠ 未找到图标文件，将使用默认图标")
    
    print("✓ 环境检查完成")
    return True

def install_dependencies():
    """安装打包依赖"""
    print("正在检查并安装依赖...")
    
    dependencies = ['pyinstaller>=5.13.0']
    
    for dep in dependencies:
        try:
            # 尝试导入检查是否已安装
            if 'pyinstaller' in dep:
                import PyInstaller
                print(f"✓ {dep.split('>=')[0]} 已安装")
                continue
        except ImportError:
            pass
        
        # 安装依赖
        try:
            print(f"正在安装 {dep}...")
            subprocess.run([sys.executable, '-m', 'pip', 'install', dep], 
                         check=True, capture_output=True, text=True)
            print(f"✓ {dep} 安装成功")
        except subprocess.CalledProcessError as e:
            print(f"✗ {dep} 安装失败: {e.stderr}")
            return False
    
    return True

def create_spec_file():
    """创建PyInstaller规格文件"""
    print("正在创建打包配置...")
    
    # 检查可用的图标
    icon_file = None
    for icon in ['C.ico', 'R.ico']:
        if Path(icon).exists():
            icon_file = icon
            break
    
    # 数据文件列表
    datas = []
    if Path('C.ico').exists():
        datas.append("('C.ico', '.')")
    if Path('R.ico').exists():
        datas.append("('R.ico', '.')")
    
    datas_str = "[" + ", ".join(datas) + "]" if datas else "[]"
    
    # 图标配置
    icon_config = f"icon='{icon_file}'" if icon_file else "icon=None"
    
    spec_content = f'''# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(
    ['client.py'],
    pathex=[],
    binaries=[],
    datas={datas_str},
         hiddenimports=[
         'win32gui',
         'win32con', 
         'win32api',
         'win32clipboard',
         'pynput',
         'psutil',
         'PySide6.QtCore',
         'PySide6.QtWidgets',
         'PySide6.QtGui',
         'security_utils',
         'automation',
         'ui_components',
         'coordinate_capture',
         'dialogs',
         'winreg',
         'ctypes',
         'ctypes.wintypes',
         'threading',
         'hashlib',
     ],
    hookspath=[],
    hooksconfig={{}},
    runtime_hooks=[],
    excludes=[
        'matplotlib',
        'numpy',
        'pandas',
        'PIL',
        'cv2',
        'scipy',
        'sklearn',
        'tensorflow',
        'torch',
        'tkinter',
        'PyQt5',
        'PyQt6',
        'wx',
        'jupyter',
        'IPython',
        'notebook',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='AutomationTool',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    {icon_config},
)
'''
    
    with open('automation_tool.spec', 'w', encoding='utf-8') as f:
        f.write(spec_content)
    
    print("✓ 打包配置创建完成")
    return True

def clean_previous_build():
    """清理之前的构建文件"""
    print("正在清理之前的构建文件...")
    
    dirs_to_clean = ['build', 'dist', '__pycache__']
    files_to_clean = ['automation_tool.spec']
    
    for dir_name in dirs_to_clean:
        dir_path = Path(dir_name)
        if dir_path.exists():
            shutil.rmtree(dir_path)
            print(f"✓ 清理目录: {dir_name}")
    
    for file_name in files_to_clean:
        file_path = Path(file_name)
        if file_path.exists():
            file_path.unlink()
            print(f"✓ 清理文件: {file_name}")

def build_executable():
    """执行打包"""
    print("开始打包，请耐心等待...")
    print("=" * 50)
    
    cmd = [
        sys.executable, '-m', 'PyInstaller',
        '--clean',
        '--noconfirm',
        'automation_tool.spec'
    ]
    
    try:
        # 实时显示打包过程
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            universal_newlines=True
        )
        
        # 实时输出
        while True:
            output = process.stdout.readline()
            if output == '' and process.poll() is not None:
                break
            if output:
                print(output.strip())
        
        return_code = process.poll()
        
        if return_code == 0:
            print("=" * 50)
            print("✓ 打包完成！")
            return True
        else:
            print("=" * 50)
            print("✗ 打包失败")
            return False
            
    except Exception as e:
        print(f"✗ 打包过程中发生错误: {e}")
        return False

def verify_build():
    """验证打包结果"""
    print("正在验证打包结果...")
    
    exe_path = Path('dist/AutomationTool.exe')
    if exe_path.exists():
        file_size = exe_path.stat().st_size / 1024 / 1024  # MB
        print(f"✓ 打包成功！")
        print(f"  输出文件: {exe_path.absolute()}")
        print(f"  文件大小: {file_size:.1f} MB")
        print(f"  创建时间: {exe_path.stat().st_mtime}")
        return True
    else:
        print("✗ 未找到输出的exe文件")
        return False

def cleanup_temp_files():
    """清理临时文件"""
    print("正在清理临时文件...")
    
    temp_items = [
        'automation_tool.spec',
        'build',
        '__pycache__'
    ]
    
    for item in temp_items:
        path = Path(item)
        if path.exists():
            if path.is_dir():
                shutil.rmtree(path)
            else:
                path.unlink()
            print(f"✓ 清理: {item}")

def main():
    """主函数"""
    print("=" * 60)
    print("🚀 自动化工具 - EXE打包脚本")
    print("=" * 60)
    print()
    
    try:
        # 步骤1: 检查环境
        if not check_environment():
            return False
        print()
        
        # 步骤2: 安装依赖
        if not install_dependencies():
            return False
        print()
        
        # 步骤3: 清理之前的构建
        clean_previous_build()
        print()
        
        # 步骤4: 创建配置文件
        if not create_spec_file():
            return False
        print()
        
        # 步骤5: 执行打包
        if not build_executable():
            return False
        print()
        
        # 步骤6: 验证结果
        if not verify_build():
            return False
        print()
        
        # 成功完成
        print("🎉 打包流程全部完成！")
        print()
        print("📋 使用说明:")
        print("  1. 可执行文件位置: dist/AutomationTool.exe")
        print("  2. JSON配置数据已内嵌在程序中")
        print("  3. 程序完全独立，无需外部文件")
        print("  4. 包含安全保护功能")
        print()
        
        return True
        
    except KeyboardInterrupt:
        print("\n⚠ 用户中断了打包过程")
        return False
    except Exception as e:
        print(f"\n✗ 打包过程中发生未预期的错误: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        # 总是清理临时文件
        print("正在执行最终清理...")
        cleanup_temp_files()

if __name__ == '__main__':
    print("开始执行打包脚本...")
    success = main()
    
    if success:
        print("\n✅ 打包成功完成！")
        print("可以在 dist/ 目录中找到 AutomationTool.exe")
    else:
        print("\n❌ 打包失败，请检查上述错误信息")
    
    # 等待用户确认
    input("\n按回车键退出...")

