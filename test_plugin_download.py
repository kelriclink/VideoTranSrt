#!/usr/bin/env python3
"""
测试插件化下载系统
"""

import sys
import os
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from video2srt.plugin_download_manager import get_download_manager

def test_plugin_download_system():
    """测试插件化下载系统"""
    print("=== 测试插件化下载系统 ===")
    
    try:
        # 获取下载管理器
        download_manager = get_download_manager()
        print("✓ 下载管理器初始化成功")
        
        # 获取所有可用模型
        all_models = download_manager.get_all_models()
        print(f"✓ 找到 {len(all_models)} 个可用模型")
        
        # 显示模型信息
        print("\n=== 可用模型列表 ===")
        for model_name, model_info in all_models.items():
            print(f"模型: {model_name}")
            print(f"  插件: {model_info.get('plugin_name', 'Unknown')}")
            print(f"  类型: {model_info.get('type', 'Unknown')}")
            print(f"  大小: {model_info.get('size', 'Unknown')}")
            print(f"  已下载: {model_info.get('downloaded', False)}")
            print(f"  语言: {model_info.get('language', 'Unknown')}")
            print()
        
        # 获取插件信息
        plugins = download_manager.get_available_plugins()
        print(f"=== 可用插件列表 ({len(plugins)} 个) ===")
        for plugin_name, plugin_info in plugins.items():
            print(f"插件: {plugin_name}")
            print(f"  版本: {plugin_info.get('version', 'Unknown')}")
            print(f"  支持的模型: {len(plugin_info.get('models', []))}")
            print()
        
        print("✓ 插件化下载系统测试完成")
        return True
        
    except Exception as e:
        print(f"✗ 测试失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_plugin_download_system()
    sys.exit(0 if success else 1)