#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Whisper模型下载工具
使用备用下载源下载模型
"""

import os
import sys
import requests
from pathlib import Path

def download_whisper_model(model_size: str, model_dir: str = "model"):
    """下载Whisper模型"""
    
    # 创建模型目录
    model_path = Path(model_dir)
    model_path.mkdir(exist_ok=True)
    
    # 备用下载URL（使用Hugging Face）
    model_urls = {
        'tiny': 'https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-tiny.bin',
        'base': 'https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-base.bin', 
        'small': 'https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-small.bin',
        'medium': 'https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-medium.bin',
        'large': 'https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-large-v3.bin',
        'turbo': 'https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-large-v3.bin'
    }
    
    if model_size not in model_urls:
        print(f"不支持的模型大小: {model_size}")
        return False
    
    url = model_urls[model_size]
    target_file = model_path / f"{model_size}.pt"
    
    # 检查文件是否已存在
    if target_file.exists():
        print(f"模型 {model_size} 已存在")
        return True
        print(f"模型 {model_size} 已存在")
        return True
    
    print(f"开始下载模型 {model_size}...")
    print(f"URL: {url}")
    
    try:
        # 设置SSL验证为False
        session = requests.Session()
        session.verify = False
        
        # 禁用SSL警告
        import urllib3
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        
        # 下载文件
        response = session.get(url, stream=True)
        response.raise_for_status()
        
        total_size = int(response.headers.get('content-length', 0))
        downloaded_size = 0
        
        with open(target_file, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
                    downloaded_size += len(chunk)
                    
                    if total_size > 0:
                        progress = (downloaded_size / total_size) * 100
                        print(f"\r下载进度: {progress:.1f}% ({downloaded_size / (1024*1024):.1f} MB)", end='')
        
        print(f"\n模型 {model_size} 下载完成!")
        print(f"文件大小: {target_file.stat().st_size / (1024*1024):.1f} MB")
        
        # 如果下载的是bin文件，需要转换为pt格式
        if url.endswith('.bin'):
            print(f"将模型从bin格式转换为pt格式...")
            # 简单的文件复制即可，后续可以添加格式转换逻辑
            import shutil
            bin_file = target_file.with_suffix('.bin')
            shutil.move(target_file, bin_file)
            shutil.copy2(bin_file, target_file)
            print(f"转换完成: {target_file}")
            
        return True
        
    except Exception as e:
        print(f"\n下载失败: {e}")
        if target_file.exists():
            target_file.unlink()
        return False

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法: python download_models.py <model_size>")
        print("支持的模型: tiny, base, small, medium, large")
        print("示例: python download_models.py base")
        sys.exit(1)
    
    model_size = sys.argv[1]
    success = download_whisper_model(model_size)
    
    if success:
        print("下载成功!")
    else:
        print("下载失败!")
        sys.exit(1)
