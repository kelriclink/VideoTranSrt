#!/usr/bin/env python3
"""
创建测试音频文件
"""

import numpy as np
import wave
import os

def create_test_audio(filename="test_audio.wav", duration=3, sample_rate=16000):
    """创建一个简单的测试音频文件"""
    
    # 生成一个简单的正弦波音频
    t = np.linspace(0, duration, int(sample_rate * duration), False)
    
    # 创建多个频率的正弦波混合
    frequencies = [440, 554, 659]  # A, C#, E 和弦
    audio = np.zeros_like(t)
    
    for freq in frequencies:
        audio += np.sin(2 * np.pi * freq * t) / len(frequencies)
    
    # 添加一些变化使其更像语音
    envelope = np.exp(-t / duration)  # 衰减包络
    audio = audio * envelope * 0.3  # 降低音量
    
    # 转换为16位整数
    audio_int = (audio * 32767).astype(np.int16)
    
    # 保存为WAV文件
    with wave.open(filename, 'w') as wav_file:
        wav_file.setnchannels(1)  # 单声道
        wav_file.setsampwidth(2)  # 16位
        wav_file.setframerate(sample_rate)
        wav_file.writeframes(audio_int.tobytes())
    
    print(f"创建测试音频文件: {filename}")
    print(f"时长: {duration}秒, 采样率: {sample_rate}Hz")
    
    return filename

if __name__ == "__main__":
    # 创建测试音频文件
    test_file = create_test_audio("testvideo/test_audio.wav")
    
    # 检查文件是否创建成功
    if os.path.exists(test_file):
        file_size = os.path.getsize(test_file)
        print(f"文件大小: {file_size} 字节")
        print("✓ 测试音频文件创建成功")
    else:
        print("✗ 测试音频文件创建失败")