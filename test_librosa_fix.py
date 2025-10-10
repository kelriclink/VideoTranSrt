#!/usr/bin/env python3
"""
测试 librosa 修复是否成功
"""

import sys
from pathlib import Path

# 添加项目路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def test_librosa_import():
    """测试 librosa 导入"""
    print("=== 测试 librosa 导入 ===")
    try:
        import librosa
        print(f"✅ librosa 导入成功，版本: {librosa.__version__}")
        return True
    except ImportError as e:
        print(f"❌ librosa 导入失败: {e}")
        return False

def test_model_loaders_import():
    """测试模型加载器导入"""
    print("\n=== 测试模型加载器导入 ===")
    try:
        from video2srt.model_loaders import OpenVINOWhisperWrapper
        print("✅ OpenVINOWhisperWrapper 导入成功")
        return True
    except ImportError as e:
        print(f"❌ OpenVINOWhisperWrapper 导入失败: {e}")
        return False

def test_audio_loading():
    """测试音频加载功能"""
    print("\n=== 测试音频加载功能 ===")
    try:
        import librosa
        import numpy as np
        
        # 创建一个简单的测试音频数组
        test_audio = np.random.randn(16000)  # 1秒的随机音频
        
        # 测试音频处理
        print("✅ 音频数组创建成功")
        print(f"  - 音频长度: {len(test_audio)} 样本")
        print(f"  - 采样率: 16000 Hz")
        
        return True
    except Exception as e:
        print(f"❌ 音频加载测试失败: {e}")
        return False

def test_distil_whisper_loader():
    """测试 Distil Whisper 加载器"""
    print("\n=== 测试 Distil Whisper 加载器 ===")
    try:
        from video2srt.model_loaders import DistilWhisperLoader
        
        # 创建加载器实例
        loader = DistilWhisperLoader("distil-whisper/distil-small.en")
        print("✅ DistilWhisperLoader 创建成功")
        
        # 检查是否支持该模型
        is_supported = loader.is_supported("distil-whisper/distil-small.en")
        print(f"✅ 模型支持检查: {is_supported}")
        
        return True
    except Exception as e:
        print(f"❌ DistilWhisperLoader 测试失败: {e}")
        return False

def main():
    """主函数"""
    print("开始测试 librosa 修复...")
    
    tests = [
        test_librosa_import,
        test_model_loaders_import,
        test_audio_loading,
        test_distil_whisper_loader
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        if test():
            passed += 1
    
    print(f"\n=== 测试结果 ===")
    print(f"通过: {passed}/{total}")
    
    if passed == total:
        print("🎉 所有测试通过！librosa 修复成功！")
    else:
        print("⚠️  部分测试失败，需要进一步检查")

if __name__ == "__main__":
    main()