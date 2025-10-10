#!/usr/bin/env python3
"""测试插件系统和下载功能"""

import sys
from pathlib import Path

# 添加项目根目录到Python路径
current_dir = Path(__file__).parent
if str(current_dir) not in sys.path:
    sys.path.insert(0, str(current_dir))

from video2srt.plugins.manager import plugin_manager
from video2srt.plugin_download_manager import PluginDownloadManager

def test_plugin_registration():
    """测试插件注册"""
    print("=== 测试插件注册 ===")
    plugins = plugin_manager.list_plugins()
    print(f"已注册的插件数量: {len(plugins)}")
    for plugin_name in plugins:
        print(f"- {plugin_name}")
    print()

def test_available_models():
    """测试可用模型"""
    print("=== 测试可用模型 ===")
    try:
        dm = PluginDownloadManager()
        models = dm.get_all_available_models()
        print(f"可用模型数量: {len(models)}")
        
        # 按插件分组显示
        plugin_models = {}
        for model_name, model_info in models.items():
            plugin_name = model_info.get('plugin_name', 'unknown')
            if plugin_name not in plugin_models:
                plugin_models[plugin_name] = []
            plugin_models[plugin_name].append(model_name)
        
        for plugin_name, model_list in plugin_models.items():
            print(f"\n{plugin_name} 插件:")
            for model in model_list:
                print(f"  - {model}")
                
    except Exception as e:
        print(f"测试可用模型失败: {e}")
    print()

def test_download_urls():
    """测试下载URL的有效性（已简化，仅检查模型列表存在）"""
    print("=== 测试下载URL（简化） ===")
    try:
        dm = PluginDownloadManager()
        models = dm.get_all_available_models()
        print(f"可用模型数量: {len(models)}")
        # 仅打印标准 Whisper 模型，不再测试 Distil/OpenVINO URL
        for name, info in models.items():
            if info.get('plugin_name') == 'standard_whisper':
                print(f"  - {name}")
    except Exception as e:
        print(f"测试下载URL失败: {e}")

if __name__ == "__main__":
    test_plugin_registration()
    test_available_models()
    test_download_urls()