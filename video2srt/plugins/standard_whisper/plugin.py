"""
标准Whisper模型加载器插件
"""

import os
import whisper
import shutil
import time
import requests
import ssl
import urllib3
from pathlib import Path
from typing import List, Optional, Dict, Any, Callable
from ..base import BaseModelLoaderPlugin

# 禁用SSL警告和验证
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
ssl._create_default_https_context = ssl._create_unverified_context


class StandardWhisperPlugin(BaseModelLoaderPlugin):
    """标准Whisper模型加载器插件"""
    
    plugin_name = "standard_whisper"
    plugin_version = "1.0.0"
    
    def __init__(self, model_size: str, model_path: Optional[str] = None, device: str = "cpu", **kwargs):
        super().__init__(model_size, model_path, **kwargs)
        self.device = device
    
    @property
    def supported_models(self) -> List[str]:
        """支持的标准Whisper模型列表"""
        return [
            'tiny', 'tiny.en', 'base', 'base.en', 'small', 'small.en',
            'medium', 'medium.en', 'large', 'large-v1', 'large-v2', 
            'large-v3', 'large-v3-turbo', 'turbo'
        ]
    
    def is_supported(self, model_size: str) -> bool:
        """检查是否为标准Whisper模型"""
        return model_size in self.supported_models
    
    def validate_environment(self) -> bool:
        """验证运行环境"""
        try:
            import whisper
            return True
        except ImportError:
            return False
    
    def get_requirements(self) -> List[str]:
        """获取依赖包列表"""
        return ["openai-whisper", "torch"]
    
    def load(self):
        """加载标准Whisper模型"""
        if self._model is not None:
            return self._model
            
        print(f"使用标准Whisper插件加载模型: {self.model_size}")
        
        # 清理可能被OpenVINO污染的缓存
        self._clean_whisper_cache()
        
        # 设置模型缓存目录
        os.environ['WHISPER_CACHE_DIR'] = str(self.model_path)
        
        try:
            self._model = whisper.load_model(self.model_size, device=self.device)
            print(f"标准Whisper模型加载成功，设备: {self.device}")
            print(f"模型存储路径: {self.model_path}")
            return self._model
        except Exception as e:
            raise RuntimeError(f"标准Whisper模型加载失败: {e}")
    
    def _clean_whisper_cache(self):
        """清理可能被OpenVINO污染的Whisper缓存"""
        # 清理可能的缓存目录
        cache_dirs = [
            self.model_path / ".cache",
            Path.home() / ".cache" / "whisper",
            Path.home() / ".cache" / "torch" / "hub" / "checkpoints"
        ]
        
        for cache_dir in cache_dirs:
            if cache_dir.exists():
                try:
                    # 只删除可能被OpenVINO污染的.pt文件
                    for pt_file in cache_dir.glob("*.pt"):
                        try:
                            # 尝试加载文件头，如果包含openvino标记则删除
                            with open(pt_file, 'rb') as f:
                                header = f.read(1024)
                            
                            # 检查二进制内容中是否包含openvino标记
                            if b'openvino' in header.lower():
                                print(f"删除被OpenVINO污染的模型文件: {pt_file}")
                                # 确保文件句柄已关闭
                                time.sleep(0.1)
                                try:
                                    pt_file.unlink()
                                except PermissionError:
                                    # 如果权限不足，尝试使用shutil.rmtree
                                    try:
                                        os.remove(str(pt_file))
                                    except Exception:
                                        print(f"无法删除文件: {pt_file}")
                        except Exception as e:
                            # 如果无法读取或删除，跳过
                            print(f"处理文件时出错 {pt_file}: {e}")
                            continue
                except Exception as e:
                    print(f"清理缓存时出错: {e}")
                    continue
    
    # 模型下载相关方法
    
    def get_downloadable_models(self) -> Dict[str, Dict[str, Any]]:
        """获取Standard Whisper支持下载的模型列表"""
        return {
            # 英语专用模型
            "tiny.en": {
                "size": "39 MB",
                "description": "英语专用，适合快速测试",
                "download_urls": [
                    "https://openaipublic.azureedge.net/main/whisper/models/d3dd57d32accea0b295c96e26691aa14d8822fac7d9d27d5dc00b4ca2826dd03/tiny.en.pt",
                    "https://huggingface.co/openai/whisper-tiny.en/resolve/main/pytorch_model.bin"
                ],
                "type": "英语专用",
                "language": "英语",
                "accuracy": "较低",
                "speed": "最快"
            },
            "base.en": {
                "size": "74 MB",
                "description": "英语专用，平衡速度和准确性",
                "download_urls": [
                    "https://openaipublic.azureedge.net/main/whisper/models/25a8566e1d0c1e2231d1c762132cd20e0f96a85d16145c3a00adf5d1ac670ead/base.en.pt",
                    "https://huggingface.co/openai/whisper-base.en/resolve/main/pytorch_model.bin"
                ],
                "type": "英语专用",
                "language": "英语",
                "accuracy": "中等",
                "speed": "快"
            },
            "small.en": {
                "size": "244 MB",
                "description": "英语专用，推荐使用",
                "download_urls": [
                    "https://openaipublic.azureedge.net/main/whisper/models/f953ad0fd29cacd07d5a9eda5624af0f6bcf2258be67c92b79389873d91e0872/small.en.pt",
                    "https://huggingface.co/openai/whisper-small.en/resolve/main/pytorch_model.bin"
                ],
                "type": "英语专用",
                "language": "英语",
                "accuracy": "较好",
                "speed": "中等"
            },
            "medium.en": {
                "size": "769 MB",
                "description": "英语专用，高质量转录",
                "download_urls": [
                    "https://openaipublic.azureedge.net/main/whisper/models/d7440d1dc186f76616474e0ff0b3b6b879abc9d1a4926b7adfa41db2d497ab4f/medium.en.pt",
                    "https://huggingface.co/openai/whisper-medium.en/resolve/main/pytorch_model.bin"
                ],
                "type": "英语专用",
                "language": "英语",
                "accuracy": "好",
                "speed": "较慢"
            },
            # 多语言模型
            "tiny": {
                "size": "39 MB",
                "description": "多语言，适合快速测试",
                "download_urls": [
                    "https://openaipublic.azureedge.net/main/whisper/models/65147644a518d12f04e32d6f3b26facc3f8dd46e5390956a9424a650c0ce22b9/tiny.pt",
                    "https://huggingface.co/openai/whisper-tiny/resolve/main/pytorch_model.bin"
                ],
                "type": "多语言",
                "language": "多语言",
                "accuracy": "较低",
                "speed": "最快"
            },
            "base": {
                "size": "74 MB",
                "description": "多语言，平衡速度和准确性",
                "download_urls": [
                    "https://openaipublic.azureedge.net/main/whisper/models/ed3a0b6b1c0edf879ad9b11b1af5a0e6ab5db9205f891f668f8b0e6c6326e34e/base.pt",
                    "https://huggingface.co/openai/whisper-base/resolve/main/pytorch_model.bin"
                ],
                "type": "多语言",
                "language": "多语言",
                "accuracy": "中等",
                "speed": "快"
            },
            "small": {
                "size": "244 MB",
                "description": "多语言，推荐使用",
                "download_urls": [
                    "https://openaipublic.azureedge.net/main/whisper/models/9ecf779972d90ba49c06d968637d720dd632c55bbf19a8717b5f295d4f83a47d/small.pt",
                    "https://huggingface.co/openai/whisper-small/resolve/main/pytorch_model.bin"
                ],
                "type": "多语言",
                "language": "多语言",
                "accuracy": "较好",
                "speed": "中等"
            },
            "medium": {
                "size": "769 MB",
                "description": "多语言，高质量转录",
                "download_urls": [
                    "https://openaipublic.azureedge.net/main/whisper/models/345ae4da62f9b3d59415adc60127b97c714f32e89e936602e85993674d08dcb1/medium.pt",
                    "https://huggingface.co/openai/whisper-medium/resolve/main/pytorch_model.bin"
                ],
                "type": "多语言",
                "language": "多语言",
                "accuracy": "好",
                "speed": "较慢"
            },
            "large": {
                "size": "1550 MB",
                "description": "多语言，最高质量",
                "download_urls": [
                    "https://openaipublic.azureedge.net/main/whisper/models/e4b87e7e0bf463eb8e6956e646f1e277e901512310def2c24bf0e11bd3c28e9a/large.pt",
                    "https://huggingface.co/openai/whisper-large/resolve/main/pytorch_model.bin"
                ],
                "type": "多语言",
                "language": "多语言",
                "accuracy": "最好",
                "speed": "慢"
            },
            "large-v2": {
                "size": "1550 MB",
                "description": "多语言，最高质量 v2",
                "download_urls": [
                    "https://openaipublic.azureedge.net/main/whisper/models/81f7c96c852ee8fc832187b0132e569d6c3065a3252ed18e56effd0b6a73e524/large-v2.pt",
                    "https://huggingface.co/openai/whisper-large-v2/resolve/main/pytorch_model.bin"
                ],
                "type": "多语言",
                "language": "多语言",
                "accuracy": "最好",
                "speed": "慢"
            },
            "large-v3": {
                "size": "1550 MB",
                "description": "多语言，最新版本",
                "download_urls": [
                    "https://openaipublic.azureedge.net/main/whisper/models/e5b1a55b89c1367dacf97e3e19bfd829a01529dbfdeefa8caeb59b3f1b81dadb/large-v3.pt",
                    "https://huggingface.co/openai/whisper-large-v3/resolve/main/pytorch_model.bin"
                ],
                "type": "多语言",
                "language": "多语言",
                "accuracy": "最好",
                "speed": "慢"
            }
        }
    
    def is_model_downloaded(self, model_name: str) -> bool:
        """检查模型是否已下载"""
        model_file = self.model_path / f"{model_name}.pt"
        return model_file.exists() and model_file.stat().st_size > 0
    
    def download_model(self, model_name: str, progress_callback: Optional[Callable] = None) -> bool:
        """下载指定模型"""
        if not self.is_supported(model_name):
            if progress_callback:
                progress_callback(model_name, 0, f"不支持的模型: {model_name}")
            return False
        
        if self.is_model_downloaded(model_name):
            if progress_callback:
                progress_callback(model_name, 100, "模型已存在")
            return True
        
        models_info = self.get_downloadable_models()
        if model_name not in models_info:
            if progress_callback:
                progress_callback(model_name, 0, f"未找到模型信息: {model_name}")
            return False
        
        model_info = models_info[model_name]
        download_urls = model_info["download_urls"]
        
        # 尝试每个下载地址
        for i, url in enumerate(download_urls):
            try:
                if progress_callback:
                    progress_callback(model_name, 0, f"尝试下载地址 {i+1}/{len(download_urls)}")
                
                success = self._download_from_url(url, model_name, progress_callback)
                if success:
                    if progress_callback:
                        progress_callback(model_name, 100, "下载完成")
                    return True
                    
            except Exception as e:
                if progress_callback:
                    progress_callback(model_name, 0, f"下载失败: {str(e)}")
                continue
        
        if progress_callback:
            progress_callback(model_name, 0, "所有下载地址都失败")
        return False
    
    def _download_from_url(self, url: str, model_name: str, progress_callback: Optional[Callable] = None) -> bool:
        """从指定URL下载模型"""
        try:
            # 创建session
            session = requests.Session()
            session.verify = False
            
            # 发送请求
            response = session.get(url, stream=True, timeout=30)
            response.raise_for_status()
            
            # 获取文件大小
            total_size = int(response.headers.get('content-length', 0))
            
            # 创建目标文件路径
            model_file = self.model_path / f"{model_name}.pt"
            self.model_path.mkdir(parents=True, exist_ok=True)
            
            # 下载文件
            downloaded = 0
            with open(model_file, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        
                        # 更新进度
                        if progress_callback and total_size > 0:
                            progress = int((downloaded / total_size) * 100)
                            progress_callback(model_name, progress, f"下载中... {downloaded}/{total_size} bytes")
            
            # 验证下载的文件
            if model_file.exists() and model_file.stat().st_size > 0:
                return True
            else:
                model_file.unlink(missing_ok=True)
                return False
                
        except Exception as e:
            print(f"下载失败: {e}")
            return False
    
    def delete_model(self, model_name: str) -> bool:
        """删除指定模型"""
        try:
            model_file = self.model_path / f"{model_name}.pt"
            if model_file.exists():
                model_file.unlink()
                return True
            return False
        except Exception as e:
            print(f"删除模型失败: {e}")
            return False
    
    def get_model_file_size(self, model_name: str) -> str:
        """获取模型文件大小"""
        try:
            model_file = self.model_path / f"{model_name}.pt"
            if model_file.exists():
                size_bytes = model_file.stat().st_size
                # 转换为人类可读的格式
                for unit in ['B', 'KB', 'MB', 'GB']:
                    if size_bytes < 1024.0:
                        return f"{size_bytes:.1f} {unit}"
                    size_bytes /= 1024.0
                return f"{size_bytes:.1f} TB"
            else:
                # 返回预期大小
                models_info = self.get_downloadable_models()
                if model_name in models_info:
                    return models_info[model_name]["size"]
                return "未知"
        except Exception:
            return "未知"