#!/usr/bin/env python3
"""
依赖测试脚本 - 验证当前环境中的包安装状态
"""

import sys
import importlib
import subprocess


def test_package_import(package_name, import_name=None):
    """测试包导入"""
    if import_name is None:
        import_name = package_name.replace('-', '_')
    
    try:
        module = importlib.import_module(import_name)
        version = getattr(module, '__version__', 'Unknown')
        print(f"✓ {package_name}: {version}")
        return True
    except ImportError as e:
        print(f"✗ {package_name}: 导入失败 - {e}")
        return False


def get_pip_package_version(package_name):
    """获取pip包版本"""
    try:
        result = subprocess.run(
            [sys.executable, "-m", "pip", "show", package_name],
            capture_output=True,
            text=True,
            check=True
        )
        for line in result.stdout.split('\n'):
            if line.startswith('Version:'):
                return line.split(':', 1)[1].strip()
    except:
        pass
    return None


def main():
    """主测试函数"""
    print("=== 依赖包测试 ===\n")
    
    # 核心依赖
    print("核心依赖:")
    test_package_import("torch")
    test_package_import("torchaudio")
    test_package_import("transformers")
    test_package_import("openai-whisper", "whisper")
    
    # 已移除 Intel GPU/OpenVINO 相关依赖的强制检查
    
    print("\n其他依赖:")
    test_package_import("PyQt6", "PyQt6")
    test_package_import("ffmpeg-python", "ffmpeg")
    
    # 注：已移除 OpenVINO 设备测试，以避免对特定硬件/库的依赖
    
    print("\n=== 测试完成 ===")


if __name__ == "__main__":
    main()