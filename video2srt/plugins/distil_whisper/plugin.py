"""
Distil-Whisper模型加载器插件
"""

import os
import requests
import ssl
import urllib3
from pathlib import Path
from typing import List, Optional, Dict, Any, Callable
from ..base import BaseModelLoaderPlugin
from ..intel_gpu.plugin import OpenVINOWhisperWrapper
from ...huggingface_validator import HuggingFaceValidator

# 禁用SSL警告和验证
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
ssl._create_default_https_context = ssl._create_unverified_context


class DistilWhisperPlugin(BaseModelLoaderPlugin):
    """Distil-Whisper模型加载器插件"""
    
    plugin_name = "distil_whisper"
    plugin_version = "1.0.0"
    
    @property
    def supported_models(self) -> List[str]:
        """支持的Distil-Whisper模型列表"""
        return [
            "distil-whisper/distil-large-v2",
            "distil-whisper/distil-large-v3", 
            "distil-whisper/distil-large-v3.5",
            "distil-whisper/distil-medium.en",
            "distil-whisper/distil-small.en"
        ]
    
    def is_supported(self, model_size: str) -> bool:
        """检查是否为Distil-Whisper模型"""
        return model_size.startswith("distil-whisper/")
    
    def validate_environment(self) -> bool:
        """验证运行环境"""
        try:
            from optimum.intel.openvino import OVModelForSpeechSeq2Seq
            from transformers import AutoProcessor
            return True
        except ImportError:
            return False
    
    def get_requirements(self) -> List[str]:
        """获取依赖包列表"""
        return ["optimum[openvino]", "transformers", "openvino"]
    
    def load(self):
        """加载Distil-Whisper模型"""
        if self._model is not None:
            return self._model
            
        print(f"使用Distil-Whisper插件加载模型: {self.model_size}")
        
        # 查找本地模型
        folder_name = self.model_size.replace("/", "_")
        model_path = self.model_path / folder_name
        
        if not model_path.exists():
            raise RuntimeError(f"未找到Distil-Whisper模型: {self.model_size}")
        
        try:
            from optimum.intel.openvino import OVModelForSpeechSeq2Seq
            from transformers import AutoProcessor
            
            print("正在加载Distil-Whisper OpenVINO模型...")
            
            model = OVModelForSpeechSeq2Seq.from_pretrained(
                model_path,
                compile=False
            )
            
            # 编译到CPU（Distil模型通常在CPU上运行良好）
            model.to("CPU")
            model.compile()
            
            processor = AutoProcessor.from_pretrained(model_path)
            
            self._model = OpenVINOWhisperWrapper(model, processor)
            print("Distil-Whisper模型加载成功")
            return self._model
            
        except Exception as e:
            raise RuntimeError(f"Distil-Whisper模型加载失败: {e}")
    
    # 模型下载相关方法
    
    def get_downloadable_models(self) -> Dict[str, Dict[str, Any]]:
        """获取Distil-Whisper支持下载的模型列表"""
        return {
            "distil-whisper/distil-large-v2": {
                "size": "756 MB",
                "description": "Distil-Whisper大型模型v2，速度快，准确度高",
                "download_urls": [
                    "https://huggingface.co/distil-whisper/distil-large-v2/resolve/main/config.json",
                    "https://huggingface.co/distil-whisper/distil-large-v2/resolve/main/model.safetensors",
                    "https://huggingface.co/distil-whisper/distil-large-v2/resolve/main/tokenizer.json",
                    "https://huggingface.co/distil-whisper/distil-large-v2/resolve/main/tokenizer_config.json",
                    "https://huggingface.co/distil-whisper/distil-large-v2/resolve/main/preprocessor_config.json",
                    "https://huggingface.co/distil-whisper/distil-large-v2/resolve/main/generation_config.json",
                    "https://huggingface.co/distil-whisper/distil-large-v2/resolve/main/vocab.json",
                    "https://huggingface.co/distil-whisper/distil-large-v2/resolve/main/merges.txt",
                    "https://huggingface.co/distil-whisper/distil-large-v2/resolve/main/normalizer.json",
                    "https://huggingface.co/distil-whisper/distil-large-v2/resolve/main/added_tokens.json",
                    "https://huggingface.co/distil-whisper/distil-large-v2/resolve/main/special_tokens_map.json"
                ],
                "type": "Distil-Whisper",
                "language": "英语",
                "accuracy": "高",
                "speed": "快"
            },
            "distil-whisper/distil-large-v3.5": {
                "size": "756 MB",
                "description": "Distil-Whisper大型模型v3.5，最新优化版本，性能更佳",
                "download_urls": [
                    "https://huggingface.co/distil-whisper/distil-large-v3.5/resolve/main/config.json",
                    "https://huggingface.co/distil-whisper/distil-large-v3.5/resolve/main/model.safetensors",
                    "https://huggingface.co/distil-whisper/distil-large-v3.5/resolve/main/tokenizer.json",
                    "https://huggingface.co/distil-whisper/distil-large-v3.5/resolve/main/tokenizer_config.json",
                    "https://huggingface.co/distil-whisper/distil-large-v3.5/resolve/main/preprocessor_config.json",
                    "https://huggingface.co/distil-whisper/distil-large-v3.5/resolve/main/generation_config.json",
                    "https://huggingface.co/distil-whisper/distil-large-v3.5/resolve/main/vocab.json",
                    "https://huggingface.co/distil-whisper/distil-large-v3.5/resolve/main/merges.txt",
                    "https://huggingface.co/distil-whisper/distil-large-v3.5/resolve/main/added_tokens.json",
                    "https://huggingface.co/distil-whisper/distil-large-v3.5/resolve/main/special_tokens_map.json"
                ],
                "type": "Distil-Whisper",
                "language": "英语",
                "accuracy": "高",
                "speed": "快"
            },
            "distil-whisper/distil-large-v3": {
                "size": "756 MB",
                "description": "Distil-Whisper大型模型v3，最新版本",
                "download_urls": [
                    "https://huggingface.co/distil-whisper/distil-large-v3/resolve/main/config.json",
                    "https://huggingface.co/distil-whisper/distil-large-v3/resolve/main/model.safetensors",
                    "https://huggingface.co/distil-whisper/distil-large-v3/resolve/main/tokenizer.json",
                    "https://huggingface.co/distil-whisper/distil-large-v3/resolve/main/tokenizer_config.json",
                    "https://huggingface.co/distil-whisper/distil-large-v3/resolve/main/preprocessor_config.json",
                    "https://huggingface.co/distil-whisper/distil-large-v3/resolve/main/generation_config.json",
                    "https://huggingface.co/distil-whisper/distil-large-v3/resolve/main/vocab.json",
                    "https://huggingface.co/distil-whisper/distil-large-v3/resolve/main/merges.txt",
                    "https://huggingface.co/distil-whisper/distil-large-v3/resolve/main/normalizer.json",
                    "https://huggingface.co/distil-whisper/distil-large-v3/resolve/main/added_tokens.json",
                    "https://huggingface.co/distil-whisper/distil-large-v3/resolve/main/special_tokens_map.json"
                ],
                "type": "Distil-Whisper",
                "language": "英语",
                "accuracy": "高",
                "speed": "快"
            },
            "distil-whisper/distil-medium.en": {
                "size": "394 MB",
                "description": "Distil-Whisper中型英语模型",
                "download_urls": [
                    "https://huggingface.co/distil-whisper/distil-medium.en/resolve/main/config.json",
                    "https://huggingface.co/distil-whisper/distil-medium.en/resolve/main/model.safetensors",
                    "https://huggingface.co/distil-whisper/distil-medium.en/resolve/main/tokenizer.json",
                    "https://huggingface.co/distil-whisper/distil-medium.en/resolve/main/tokenizer_config.json",
                    "https://huggingface.co/distil-whisper/distil-medium.en/resolve/main/preprocessor_config.json",
                    "https://huggingface.co/distil-whisper/distil-medium.en/resolve/main/generation_config.json",
                    "https://huggingface.co/distil-whisper/distil-medium.en/resolve/main/vocab.json",
                    "https://huggingface.co/distil-whisper/distil-medium.en/resolve/main/merges.txt",
                    "https://huggingface.co/distil-whisper/distil-medium.en/resolve/main/normalizer.json",
                    "https://huggingface.co/distil-whisper/distil-medium.en/resolve/main/added_tokens.json",
                    "https://huggingface.co/distil-whisper/distil-medium.en/resolve/main/special_tokens_map.json"
                ],
                "type": "Distil-Whisper",
                "language": "英语",
                "accuracy": "中高",
                "speed": "快"
            },
            "distil-whisper/distil-small.en": {
                "size": "166 MB",
                "description": "Distil-Whisper小型英语模型",
                "download_urls": [
                    "https://huggingface.co/distil-whisper/distil-small.en/resolve/main/config.json",
                    "https://huggingface.co/distil-whisper/distil-small.en/resolve/main/model.safetensors",
                    "https://huggingface.co/distil-whisper/distil-small.en/resolve/main/tokenizer.json",
                    "https://huggingface.co/distil-whisper/distil-small.en/resolve/main/tokenizer_config.json",
                    "https://huggingface.co/distil-whisper/distil-small.en/resolve/main/preprocessor_config.json",
                    "https://huggingface.co/distil-whisper/distil-small.en/resolve/main/generation_config.json",
                    "https://huggingface.co/distil-whisper/distil-small.en/resolve/main/vocab.json",
                    "https://huggingface.co/distil-whisper/distil-small.en/resolve/main/merges.txt",
                    "https://huggingface.co/distil-whisper/distil-small.en/resolve/main/normalizer.json",
                    "https://huggingface.co/distil-whisper/distil-small.en/resolve/main/added_tokens.json",
                    "https://huggingface.co/distil-whisper/distil-small.en/resolve/main/special_tokens_map.json"
                ],
                "type": "Distil-Whisper",
                "language": "英语",
                "accuracy": "中等",
                "speed": "很快"
            }
        }
    
    def is_model_downloaded(self, model_name: str) -> bool:
        """检查模型是否已下载"""
        folder_name = model_name.replace("/", "_")
        model_dir = self.model_path / folder_name
        
        # 获取该模型的实际文件列表
        downloadable_models = self.get_downloadable_models()
        if model_name not in downloadable_models:
            return False
            
        # 从下载URL中提取文件名
        download_urls = downloadable_models[model_name]["download_urls"]
        required_files = [url.split("/")[-1] for url in download_urls]
        
        return all((model_dir / file).exists() for file in required_files)
    
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
        
        try:
            # 获取模型的下载URL列表
            model_info = self.get_downloadable_models().get(model_name)
            if not model_info:
                if progress_callback:
                    progress_callback(model_name, 0, f"不支持的模型: {model_name}")
                return False
            
            download_urls = model_info.get("download_urls", [])
            if not download_urls:
                if progress_callback:
                    progress_callback(model_name, 0, f"没有找到下载链接: {model_name}")
                return False
            
            # 预下载验证：检查文件列表是否与Hugging Face实际文件匹配
            if progress_callback:
                progress_callback(model_name, 5, "验证文件列表...")
            
            validator = HuggingFaceValidator()
            is_valid, report = validator.validate_download_urls(model_name, download_urls)
            
            if not is_valid:
                print(f"\n警告: 模型 {model_name} 的文件列表与Hugging Face实际文件不匹配")
                validator.print_validation_report(report)
                
                # 获取修正后的文件列表
                expected_files = []
                for url in download_urls:
                    if "/resolve/main/" in url:
                        filename = url.split("/resolve/main/")[-1]
                        expected_files.append(filename)
                
                corrected_files = validator.get_corrected_file_list(model_name, expected_files)
                if corrected_files:
                    print(f"将使用修正后的文件列表进行下载...")
                    # 重新构建下载URL列表
                    base_url = download_urls[0].split("/resolve/main/")[0] + "/resolve/main/"
                    download_urls = [base_url + filename for filename in corrected_files]
                else:
                    if progress_callback:
                        progress_callback(model_name, 0, "无法获取有效的文件列表")
                    return False
            
            # 获取模型目录
            folder_name = model_name.replace("/", "_")
            model_dir = self.model_path / folder_name
            model_dir.mkdir(parents=True, exist_ok=True)
            
            total_files = len(download_urls)
            for i, url in enumerate(download_urls):
                try:
                    filename = url.split("/")[-1]
                    if progress_callback:
                        progress_callback(model_name, int(10 + (i / total_files) * 85), f"下载 {filename}")
                    
                    success = self._download_file(url, model_dir / filename)
                    
                    if not success:
                        if progress_callback:
                            progress_callback(model_name, 0, f"下载文件失败: {filename}")
                        return False
                        
                except Exception as e:
                    if progress_callback:
                        progress_callback(model_name, 0, f"下载失败: {str(e)}")
                    return False
            
            # 创建下载完成标记文件
            (model_dir / "download_complete.txt").write_text("download completed")
            
            if progress_callback:
                progress_callback(model_name, 100, "下载完成")
            return True
            
        except Exception as e:
            if progress_callback:
                progress_callback(model_name, 0, f"下载失败: {str(e)}")
            return False
    
    def _download_file(self, url: str, file_path: Path) -> bool:
        """下载单个文件"""
        try:
            session = requests.Session()
            session.verify = False
            
            response = session.get(url, stream=True, timeout=30)
            response.raise_for_status()
            
            with open(file_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
            
            return file_path.exists() and file_path.stat().st_size > 0
            
        except Exception as e:
            print(f"下载文件失败 {url}: {e}")
            return False
    
    def delete_model(self, model_name: str) -> bool:
        """删除指定模型"""
        try:
            folder_name = model_name.replace("/", "_")
            model_dir = self.model_path / folder_name
            
            if model_dir.exists():
                import shutil
                shutil.rmtree(model_dir)
                return True
            return False
        except Exception as e:
            print(f"删除模型失败: {e}")
            return False
    
    def get_model_file_size(self, model_name: str) -> str:
        """获取模型文件大小"""
        try:
            folder_name = model_name.replace("/", "_")
            model_dir = self.model_path / folder_name
            
            if model_dir.exists():
                total_size = sum(f.stat().st_size for f in model_dir.rglob('*') if f.is_file())
                # 转换为人类可读的格式
                for unit in ['B', 'KB', 'MB', 'GB']:
                    if total_size < 1024.0:
                        return f"{total_size:.1f} {unit}"
                    total_size /= 1024.0
                return f"{total_size:.1f} TB"
            else:
                # 返回预期大小
                models_info = self.get_downloadable_models()
                if model_name in models_info:
                    return models_info[model_name]["size"]
                return "未知"
        except Exception:
            return "未知"