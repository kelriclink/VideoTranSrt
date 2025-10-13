#!/usr/bin/env python3
"""
测试翻译器选择逻辑修复
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'video2srt'))

from video2srt.models import Segment
from video2srt.translator_manager import TranslatorManager
from video2srt.config_manager import config_manager

def test_translator_selection():
    """测试翻译器选择逻辑"""
    print("=== 测试翻译器选择逻辑 ===")
    
    # 创建测试数据
    segments = [
        Segment(start=1.0, end=3.0, text="Hello world"),
        Segment(start=4.0, end=6.0, text="This is a test")
    ]
    
    # 初始化翻译器管理器
    translator_manager = TranslatorManager()
    
    # 测试Google翻译器
    print("\n1. 测试Google翻译器选择:")
    try:
        result = translator_manager.translate_with_retry(
            segments=segments,
            target_language="zh-CN",
            source_language="auto",
            preferred_translator="google"
        )
        print(f"✓ 翻译成功，使用的翻译器: {result.translator_name}")
        print(f"  翻译结果数量: {len(result.segments)}")
        for i, seg in enumerate(result.segments):
            print(f"  段落 {i+1}: {seg.text}")
    except Exception as e:
        print(f"✗ 翻译失败: {e}")
    
    # 测试配置的默认翻译器
    print("\n2. 测试配置的默认翻译器:")
    default_translator = config_manager.get_default_translator()
    print(f"  当前默认翻译器: {default_translator}")
    
    try:
        result = translator_manager.translate_with_retry(
            segments=segments,
            target_language="zh-CN",
            source_language="auto"
        )
        print(f"✓ 翻译成功，使用的翻译器: {result.translator_name}")
    except Exception as e:
        print(f"✗ 翻译失败: {e}")
    
    # 检查翻译器状态
    print("\n3. 翻译器状态检查:")
    for name, translator_info in translator_manager.translators.items():
        status = translator_info.status
        print(f"  {name}: {status}")

if __name__ == "__main__":
    test_translator_selection()