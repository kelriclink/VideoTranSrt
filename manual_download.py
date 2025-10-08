#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
手动下载Whisper模型工具
提供多种下载方式
"""

import os
import sys
import requests
import ssl
import urllib3
from pathlib import Path

# 禁用SSL警告
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
ssl._create_default_https_context = ssl._create_unverified_context

def download_model_manual(model_size: str, model_dir: str = "model"):
    """手动下载模型"""
    
    # 创建模型目录
    model_path = Path(model_dir)
    model_path.mkdir(exist_ok=True)
    
    target_file = model_path / f"{model_size}.pt"
    
    if target_file.exists():
        print(f"模型 {model_size} 已存在")
        return True
    
    print(f"开始手动下载模型 {model_size}...")
    print("请选择下载方式:")
    print("1. 使用HuggingFace (推荐)")
    print("2. 使用自定义URL")
    print("3. 跳过下载")
    
    choice = input("请输入选择 (1-3): ").strip()
    
    if choice == "1":
        return download_from_huggingface(model_size, target_file)
    elif choice == "2":
        url = input("请输入模型下载URL: ").strip()
        if url:
            return download_from_url(model_size, url, target_file)
    elif choice == "3":
        print("跳过下载")
        return False
    else:
        print("无效选择")
        return False

def download_from_huggingface(model_size: str, target_file: Path):
    """从HuggingFace下载"""
    hf_urls = {
        'tiny': 'https://huggingface.co/openai/whisper-tiny/resolve/main/pytorch_model.bin',
        'base': 'https://huggingface.co/openai/whisper-base/resolve/main/pytorch_model.bin',
        'small': 'https://huggingface.co/openai/whisper-small/resolve/main/pytorch_model.bin',
        'medium': 'https://huggingface.co/openai/whisper-medium/resolve/main/pytorch_model.bin',
        'large': 'https://huggingface.co/openai/whisper-large-v2/resolve/main/pytorch_model.bin'
    }
    
    if model_size not in hf_urls:
        print(f"不支持的模型大小: {model_size}")
        return False
    
    url = hf_urls[model_size]
    print(f"从HuggingFace下载: {url}")
    
    return download_from_url(model_size, url, target_file)

def download_from_url(model_size: str, url: str, target_file: Path):
    """从URL下载模型"""
    try:
        session = requests.Session()
        session.verify = False
        
        print(f"正在下载: {url}")
        
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
        return True
        
    except Exception as e:
        print(f"\n下载失败: {e}")
        if target_file.exists():
            target_file.unlink()
        return False

def list_available_models():
    """列出可用模型"""
    print("可用的Whisper模型:")
    print("- tiny: 39MB, 最快速度, 较低准确性")
    print("- base: 74MB, 快速, 中等准确性 (推荐)")
    print("- small: 244MB, 中等速度, 较好准确性")
    print("- medium: 769MB, 较慢, 高准确性")
    print("- large: 1550MB, 最慢, 最高准确性")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        list_available_models()
        print("\n用法: python manual_download.py <model_size>")
        print("示例: python manual_download.py base")
        sys.exit(1)
    
    model_size = sys.argv[1]
    
    if model_size not in ['tiny', 'base', 'small', 'medium', 'large']:
        print(f"不支持的模型大小: {model_size}")
        list_available_models()
        sys.exit(1)
    
    success = download_model_manual(model_size)
    
    if success:
        print("下载成功!")
    else:
        print("下载失败!")
        sys.exit(1)
