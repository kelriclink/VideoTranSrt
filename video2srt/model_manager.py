"""
模型管理模块
用于管理 Whisper 模型的下载、删除和状态检查
"""

import os
import whisper
import threading
import ssl
import urllib3
import requests
from pathlib import Path
from typing import Dict, Any, List, Optional, Callable
from .config_manager import config_manager

# 禁用SSL警告和验证
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
ssl._create_default_https_context = ssl._create_unverified_context


class ModelManager:
    """模型管理器"""
    
    def __init__(self):
        self.model_path = Path(config_manager.get_whisper_model_path())
        self.model_path.mkdir(exist_ok=True)
        self.download_progress = {}
        self.download_callbacks = {}
        
        # 创建session用于网络请求
        self.session = requests.Session()
        self.session.verify = False
        
        # 缓存的模型URL
        self.cached_urls = {}
    
    def get_model_info(self) -> Dict[str, Dict[str, Any]]:
        """获取所有模型的信息"""
        models = {
            # 英语专用模型
            "tiny.en": {
                "size": "39 MB", 
                "speed": "最快", 
                "accuracy": "较低", 
                "description": "英语专用，适合快速测试",
                "language": "英语",
                "type": "英语专用"
            },
            "base.en": {
                "size": "74 MB", 
                "speed": "快", 
                "accuracy": "中等", 
                "description": "英语专用，平衡速度和准确性",
                "language": "英语",
                "type": "英语专用"
            },
            "small.en": {
                "size": "244 MB", 
                "speed": "中等", 
                "accuracy": "较好", 
                "description": "英语专用，推荐使用",
                "language": "英语",
                "type": "英语专用"
            },
            "medium.en": {
                "size": "769 MB", 
                "speed": "较慢", 
                "accuracy": "好", 
                "description": "英语专用，高质量转录",
                "language": "英语",
                "type": "英语专用"
            },
            # 多语言模型
            "tiny": {
                "size": "39 MB", 
                "speed": "最快", 
                "accuracy": "较低", 
                "description": "多语言，适合快速测试",
                "language": "多语言",
                "type": "多语言"
            },
            "base": {
                "size": "74 MB", 
                "speed": "快", 
                "accuracy": "中等", 
                "description": "多语言，平衡速度和准确性",
                "language": "多语言",
                "type": "多语言"
            },
            "small": {
                "size": "244 MB", 
                "speed": "中等", 
                "accuracy": "较好", 
                "description": "多语言，推荐使用",
                "language": "多语言",
                "type": "多语言"
            },
            "medium": {
                "size": "769 MB", 
                "speed": "较慢", 
                "accuracy": "好", 
                "description": "多语言，高质量转录",
                "language": "多语言",
                "type": "多语言"
            },
            "large": {
                "size": "1550 MB", 
                "speed": "最慢", 
                "accuracy": "最好", 
                "description": "多语言，最高质量转录",
                "language": "多语言",
                "type": "多语言"
            }
        }
        
        # 检查每个模型是否已下载
        for model_name in models:
            models[model_name]["downloaded"] = self.is_model_downloaded(model_name)
            models[model_name]["file_size"] = self.get_model_file_size(model_name)
        
        return models
    
    def is_model_downloaded(self, model_size: str) -> bool:
        """检查模型是否已下载"""
        model_file = self.model_path / f"{model_size}.pt"
        return model_file.exists()
    
    def get_model_file_size(self, model_size: str) -> str:
        """获取模型文件大小"""
        model_file = self.model_path / f"{model_size}.pt"
        if model_file.exists():
            size_bytes = model_file.stat().st_size
            if size_bytes < 1024 * 1024:
                return f"{size_bytes / 1024:.1f} KB"
            else:
                return f"{size_bytes / (1024 * 1024):.1f} MB"
        return "未下载"
    
    def download_model(self, model_size: str, progress_callback: Optional[Callable] = None) -> bool:
        """
        下载指定模型
        
        Args:
            model_size: 模型大小
            progress_callback: 进度回调函数，参数为 (model_size, progress, status)
            
        Returns:
            是否下载成功
        """
        if self.is_model_downloaded(model_size):
            if progress_callback:
                progress_callback(model_size, 100, "已存在")
            return True
        
        # 尝试多种下载方法
        download_methods = [
            self._download_with_whisper,
            self._download_with_huggingface,
            self._download_with_direct_url
        ]
        
        for i, method in enumerate(download_methods):
            try:
                if progress_callback:
                    progress_callback(model_size, 0, f"尝试下载方法 {i+1}/3")
                
                if method(model_size, progress_callback):
                    if progress_callback:
                        progress_callback(model_size, 100, "下载完成")
                    return True
                    
            except Exception as e:
                print(f"下载方法 {i+1} 失败: {e}")
                continue
        
        # 所有方法都失败
        if progress_callback:
            progress_callback(model_size, 0, "所有下载方法都失败")
        return False
    
    def _download_with_whisper(self, model_size: str, progress_callback: Optional[Callable] = None) -> bool:
        """使用Whisper官方方法下载"""
        try:
            # 设置环境变量指定模型存储路径和SSL设置
            os.environ['WHISPER_CACHE_DIR'] = str(self.model_path)
            os.environ['PYTHONHTTPSVERIFY'] = '0'
            os.environ['CURL_CA_BUNDLE'] = ''
            
            if progress_callback:
                progress_callback(model_size, 10, "使用Whisper官方源下载")
            
            # 使用 whisper 下载模型
            model = whisper.load_model(model_size, download_root=str(self.model_path))
            return self.is_model_downloaded(model_size)
            
        except Exception as e:
            print(f"Whisper官方下载失败: {e}")
            return False
    
    def _download_with_huggingface(self, model_size: str, progress_callback: Optional[Callable] = None) -> bool:
        """使用HuggingFace下载"""
        try:
            # turbo 不提供稳定的 HuggingFace 直链，这里直接跳过
            if model_size == 'turbo':
                if progress_callback:
                    progress_callback(model_size, 0, "turbo 仅支持官方下载，跳过HuggingFace")
                return False
            if progress_callback:
                progress_callback(model_size, 20, "尝试HuggingFace源")
            
            # HuggingFace模型映射
            hf_models = {
                'tiny.en': 'openai/whisper-tiny.en',
                'base.en': 'openai/whisper-base.en',
                'small.en': 'openai/whisper-small.en',
                'medium.en': 'openai/whisper-medium.en',
                'tiny': 'openai/whisper-tiny',
                'base': 'openai/whisper-base',
                'small': 'openai/whisper-small',
                'medium': 'openai/whisper-medium',
                'large': 'openai/whisper-large-v2'
            }
            
            if model_size not in hf_models:
                return False
            
            # 尝试使用transformers下载
            try:
                from transformers import WhisperModel
                model = WhisperModel.from_pretrained(hf_models[model_size])
                
                # 保存为.pt格式
                target_path = self.model_path / f"{model_size}.pt"
                import torch
                torch.save(model.state_dict(), target_path)
                
                return self.is_model_downloaded(model_size)
                
            except ImportError:
                print("transformers库未安装，跳过HuggingFace下载")
                return False
                
        except Exception as e:
            print(f"HuggingFace下载失败: {e}")
            return False
    
    def _download_with_direct_url(self, model_size: str, progress_callback: Optional[Callable] = None) -> bool:
        """使用直接URL下载"""
        try:
            # turbo 没有稳定直链，直接返回 False 让上层走其它方式
            if model_size == 'turbo':
                if progress_callback:
                    progress_callback(model_size, 0, "turbo 无直链，跳过直链下载")
                return False
            if progress_callback:
                progress_callback(model_size, 30, "尝试动态URL下载")
            
            # 获取最佳下载URL
            best_url = self.get_best_download_url(model_size)
            
            if not best_url:
                if progress_callback:
                    progress_callback(model_size, 0, "未找到可用的下载URL")
                return False
            
            if progress_callback:
                progress_callback(model_size, 40, f"使用URL: {best_url[:50]}...")
            
            return self.download_from_url(best_url, model_size, progress_callback)
            
        except Exception as e:
            print(f"动态URL下载失败: {e}")
            return False
    
    def delete_model(self, model_size: str) -> bool:
        """
        删除指定模型
        
        Args:
            model_size: 模型大小
            
        Returns:
            是否删除成功
        """
        try:
            model_file = self.model_path / f"{model_size}.pt"
            if model_file.exists():
                model_file.unlink()
                return True
            return False
        except Exception as e:
            print(f"删除模型失败: {e}")
            return False
    
    def get_disk_usage(self) -> Dict[str, Any]:
        """获取模型文件夹的磁盘使用情况"""
        total_size = 0
        file_count = 0
        
        for file_path in self.model_path.glob("*.pt"):
            if file_path.is_file():
                total_size += file_path.stat().st_size
                file_count += 1
        
        return {
            "total_size_mb": round(total_size / (1024 * 1024), 2),
            "file_count": file_count,
            "model_path": str(self.model_path)
        }
    
    def cleanup_models(self) -> int:
        """清理所有模型文件"""
        deleted_count = 0
        for file_path in self.model_path.glob("*.pt"):
            try:
                file_path.unlink()
                deleted_count += 1
            except Exception as e:
                print(f"删除文件失败 {file_path}: {e}")
        return deleted_count
    
    def get_recommended_model(self) -> str:
        """获取推荐的模型大小"""
        # 根据系统性能推荐模型
        import torch
        
        if torch.cuda.is_available():
            # 有GPU，推荐使用较大的模型
            return "small"
        else:
            # 只有CPU，推荐使用较小的模型
            return "base"
    
    def get_english_models(self) -> List[str]:
        """获取英语专用模型列表"""
        return ["tiny.en", "base.en", "small.en", "medium.en"]
    
    def get_multilingual_models(self) -> List[str]:
        """获取多语言模型列表"""
        return ["tiny", "base", "small", "medium", "large", "turbo"]
    
    def get_all_models(self) -> List[str]:
        """获取所有模型列表"""
        return list(self.get_model_info().keys())
    
    def get_model_type(self, model_name: str) -> str:
        """获取模型类型"""
        model_info = self.get_model_info()
        if model_name in model_info:
            return model_info[model_name].get("type", "未知")
        return "未知"
    
    def upload_model(self, file_path: str, model_name: str = None) -> bool:
        """
        上传用户自定义模型
        
        Args:
            file_path: 模型文件路径
            model_name: 模型名称，如果为None则使用文件名
            
        Returns:
            是否上传成功
        """
        try:
            file_path = Path(file_path)
            if not file_path.exists():
                print(f"文件不存在: {file_path}")
                return False
            
            # 确定模型名称
            if model_name is None:
                model_name = file_path.stem
            
            # 目标路径
            target_path = self.model_path / f"{model_name}.pt"
            
            # 复制文件
            import shutil
            shutil.copy2(file_path, target_path)
            
            print(f"模型上传成功: {target_path}")
            return True
            
        except Exception as e:
            print(f"模型上传失败: {e}")
            return False
    
    def download_from_url(self, url: str, model_name: str, progress_callback: Optional[Callable] = None) -> bool:
        """
        从自定义URL下载模型
        
        Args:
            url: 下载链接
            model_name: 模型名称
            progress_callback: 进度回调函数
            
        Returns:
            是否下载成功
        """
        try:
            if progress_callback:
                progress_callback(model_name, 0, "开始下载")
            
            # 设置SSL验证为False
            session = requests.Session()
            session.verify = False
            
            # 发送请求获取文件大小
            response = session.head(url, allow_redirects=True)
            total_size = int(response.headers.get('content-length', 0))
            
            if progress_callback:
                progress_callback(model_name, 10, f"文件大小: {total_size / (1024*1024):.1f} MB")
            
            # 下载文件
            response = session.get(url, stream=True)
            response.raise_for_status()
            
            target_path = self.model_path / f"{model_name}.pt"
            downloaded_size = 0
            
            with open(target_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        downloaded_size += len(chunk)
                        
                        if total_size > 0 and progress_callback:
                            progress = int((downloaded_size / total_size) * 90) + 10  # 10-100%
                            progress_callback(model_name, progress, f"下载中... {downloaded_size / (1024*1024):.1f} MB")
            
            if progress_callback:
                progress_callback(model_name, 100, "下载完成")
            
            print(f"模型下载成功: {target_path}")
            return True
            
        except Exception as e:
            if progress_callback:
                progress_callback(model_name, 0, f"下载失败: {str(e)}")
            print(f"自定义下载失败: {e}")
            return False
    
    def list_custom_models(self) -> List[Dict[str, Any]]:
        """列出所有自定义模型"""
        custom_models = []
        
        for model_file in self.model_path.glob("*.pt"):
            if model_file.is_file():
                size_bytes = model_file.stat().st_size
                size_mb = size_bytes / (1024 * 1024)
                
                custom_models.append({
                    "name": model_file.stem,
                    "path": str(model_file),
                    "size": f"{size_mb:.1f} MB",
                    "type": "custom"
                })
        
        return custom_models
    
    def get_dynamic_download_urls(self) -> Dict[str, List[str]]:
        """动态获取模型下载URL"""
        urls = {}
        
        # 模型映射
        model_mapping = {
            'tiny.en': 'openai/whisper-tiny.en',
            'base.en': 'openai/whisper-base.en',
            'small.en': 'openai/whisper-small.en',
            'medium.en': 'openai/whisper-medium.en',
            'tiny': 'openai/whisper-tiny',
            'base': 'openai/whisper-base', 
            'small': 'openai/whisper-small',
            'medium': 'openai/whisper-medium',
            'large': 'openai/whisper-large-v2'
        }
        
        for model_size, hf_model_name in model_mapping.items():
            url_list = []
            
            # 1. HuggingFace URL
            hf_url = f"https://huggingface.co/{hf_model_name}/resolve/main/pytorch_model.bin"
            url_list.append(hf_url)
            
            # 2. GitHub releases URL
            gh_url = f"https://github.com/openai/whisper/releases/download/v20231117/whisper-{model_size}.pt"
            url_list.append(gh_url)
            
            # 3. 备用URL
            backup_urls = self._get_backup_urls(model_size)
            url_list.extend(backup_urls)
            
            urls[model_size] = url_list
        
        return urls
    
    def _get_backup_urls(self, model_size: str) -> List[str]:
        """获取备用下载URL"""
        backup_urls = {
            'tiny.en': [
                'https://openaipublic.azureedge.net/whisper/models/d3dd57d306ac5ece3e972c32e5e0e0a5b1b5e92/whisper-tiny.en.pt'
            ],
            'base.en': [
                'https://openaipublic.azureedge.net/whisper/models/25a8566e1d0c1e2231d1c762cccdc360be0c19a1/whisper-base.en.pt'
            ],
            'small.en': [
                'https://openaipublic.azureedge.net/whisper/models/f953ad0fd29cacd07d5a9eda5624af0f6bcf225/whisper-small.en.pt'
            ],
            'medium.en': [
                'https://openaipublic.azureedge.net/whisper/models/d7440d1dc186f76616474e0ff0b3b6b879abc9d1/whisper-medium.en.pt'
            ],
            'tiny': [
                'https://openaipublic.azureedge.net/whisper/models/65147644a518d12f04e32d6f3b26facc3f8dd46e/whisper-tiny.pt'
            ],
            'base': [
                'https://openaipublic.azureedge.net/whisper/models/ed3a0b6b1c0edf879ad9b11b1af5a0e6ab5db920/whisper-base.pt'
            ],
            'small': [
                'https://openaipublic.azureedge.net/whisper/models/9ecf779972d90ba49c06d968637d720dd632c55a/whisper-small.pt'
            ],
            'medium': [
                'https://openaipublic.azureedge.net/whisper/models/345ae4da62f9b3d59415adc60127b97c714f32e89a9363e3412cbe9adc78d780/whisper-medium.pt'
            ],
            'large': [
                'https://openaipublic.azureedge.net/whisper/models/81f7c96c852ee8fc832187b0132e569d6c3065a3252ed18e56effd0b6a73e524/whisper-large-v2.pt'
            ]
        }
        
        return backup_urls.get(model_size, [])
    
    def test_url_availability(self, url: str) -> bool:
        """测试URL是否可用"""
        try:
            response = self.session.head(url, timeout=5)
            return response.status_code == 200
        except:
            return False
    
    def get_best_download_url(self, model_size: str) -> Optional[str]:
        """获取最佳下载URL"""
        urls = self.get_dynamic_download_urls()
        
        if model_size not in urls:
            return None
        
        # 测试每个URL的可用性
        for url in urls[model_size]:
            if self.test_url_availability(url):
                return url
        
        return None
    
    def refresh_download_urls(self):
        """刷新下载URL缓存"""
        self.cached_urls = self.get_dynamic_download_urls()


# 全局模型管理器实例
model_manager = ModelManager()
