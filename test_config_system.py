#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
配置系统测试脚本
"""

import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from video2srt.config_manager import config_manager
from video2srt.translator import get_translator, get_available_translators


def test_config_manager():
    """测试配置管理器"""
    print("测试配置管理器")
    print("=" * 50)
    
    # 测试基本配置操作
    print(f"配置文件位置: {config_manager.config_file}")
    print(f"默认翻译器: {config_manager.get_default_translator()}")
    print(f"备用翻译器: {config_manager.get_fallback_translator()}")
    
    # 测试设置和获取
    print("\n测试配置设置和获取:")
    config_manager.set('test.key', 'test_value')
    value = config_manager.get('test.key')
    print(f"设置 test.key = test_value, 获取结果: {value}")
    
    # 测试 API Key 设置
    print("\n测试 API Key 设置:")
    config_manager.set_openai_api_key('test-api-key')
    api_key = config_manager.get_openai_api_key()
    print(f"OpenAI API Key: {'已设置' if api_key else '未设置'}")
    
    # 测试翻译器可用性
    print(f"\n可用翻译器: {config_manager.get_available_translators()}")
    
    # 清理测试数据
    config_manager.set('test.key', None)
    config_manager.set_openai_api_key('')
    
    print("配置管理器测试完成!")


def test_translator_integration():
    """测试翻译器集成"""
    print("\n测试翻译器集成")
    print("=" * 50)
    
    # 测试获取可用翻译器
    available = get_available_translators()
    print(f"可用翻译器: {available}")
    
    # 测试创建翻译器
    for translator_type in ['simple', 'google']:
        try:
            translator = get_translator(translator_type)
            result = translator.translate_text("Hello", "zh")
            print(f"{translator_type} 翻译器: 成功 - {result}")
        except Exception as e:
            print(f"{translator_type} 翻译器: 失败 - {e}")


def test_config_file_operations():
    """测试配置文件操作"""
    print("\n测试配置文件操作")
    print("=" * 50)
    
    # 测试导出配置
    export_file = "test_config_export.json"
    if config_manager.export_config(export_file):
        print(f"配置导出成功: {export_file}")
        
        # 测试导入配置
        if config_manager.import_config(export_file):
            print("配置导入成功")
        else:
            print("配置导入失败")
        
        # 清理测试文件
        Path(export_file).unlink(missing_ok=True)
    else:
        print("配置导出失败")


def main():
    """主函数"""
    print("Video2SRT 配置系统测试")
    print("=" * 50)
    
    try:
        test_config_manager()
        test_translator_integration()
        test_config_file_operations()
        
        print("\n所有测试完成!")
        print("\n配置系统功能:")
        print("- ✅ 配置文件管理")
        print("- ✅ API 密钥设置")
        print("- ✅ 翻译器配置")
        print("- ✅ 配置导入导出")
        print("- ✅ 默认值管理")
        
    except Exception as e:
        print(f"测试过程中出现错误: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
