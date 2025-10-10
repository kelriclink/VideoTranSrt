#!/usr/bin/env python3
"""
测试新的模型加载器系统
"""

import sys
from pathlib import Path

# 添加项目路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from video2srt.transcriber import Transcriber
from video2srt.model_loaders import ModelLoaderFactory

def test_model_loader_factory():
    """测试模型加载器工厂"""
    print("=== 测试模型加载器工厂 ===")
    
    # 测试标准Whisper模型
    print("\n1. 测试标准Whisper模型:")
    try:
        loader = ModelLoaderFactory.create_loader("small", None, "cpu")
        print(f"  - 创建加载器成功: {type(loader).__name__}")
    except Exception as e:
        print(f"  - 创建加载器失败: {e}")
    
    # 已移除 Intel GPU 与 Distil-Whisper 测试
    
    # 测试不支持的模型
    print("\n4. 测试不支持的模型:")
    try:
        loader = ModelLoaderFactory.create_loader("unknown-model", None, "cpu")
        print(f"  - 创建加载器成功: {type(loader).__name__}")
    except Exception as e:
        print(f"  - 创建加载器失败（预期）: {e}")

def test_transcriber_with_new_loaders():
    """测试Transcriber使用新的加载器"""
    print("\n=== 测试Transcriber使用新加载器 ===")
    
    # 测试标准模型
    print("\n1. 测试标准Whisper模型:")
    try:
        transcriber = Transcriber(model_size="small")
        print(f"  - Transcriber创建成功，模型: {transcriber.model_size}")
        print(f"  - 设备: {transcriber.device}")
    except Exception as e:
        print(f"  - Transcriber创建失败: {e}")
    
    # 已移除 Intel/OpenVINO 相关测试

def main():
    """主函数"""
    print("开始测试新的模型加载器系统...")
    
    test_model_loader_factory()
    test_transcriber_with_new_loaders()
    
    print("\n测试完成！")

if __name__ == "__main__":
    main()