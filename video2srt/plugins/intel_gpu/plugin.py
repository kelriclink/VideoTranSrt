"""
Intel GPU优化模型加载器插件
"""

import os
import numpy as np
import librosa
import requests
import ssl
import urllib3
from pathlib import Path
from typing import List, Optional, Dict, Any, Callable
from ..base import BaseModelLoaderPlugin, ModelWrapper
from ...huggingface_validator import HuggingFaceValidator
# 禁用SSL警告和验证
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
ssl._create_default_https_context = ssl._create_unverified_context


class OpenVINOWhisperWrapper(ModelWrapper):
    """OpenVINO Whisper模型包装器，提供与标准Whisper兼容的接口"""
    
    def __init__(self, model, processor):
        self.model = model
        self.processor = processor
    
    def transcribe(self, audio, **kwargs):
        """转录音频"""
        try:
            # 加载音频
            if isinstance(audio, str):
                audio_array, sr = librosa.load(audio, sr=16000)
            else:
                audio_array = audio
            
            # 预处理音频
            inputs = self.processor(audio_array, sampling_rate=16000, return_tensors="pt")
            
            # 生成转录
            predicted_ids = self.model.generate(**inputs)
            transcription = self.processor.batch_decode(predicted_ids, skip_special_tokens=True)
            
            # 获取转录文本
            text = transcription[0] if transcription else ""
            
            # 创建segments - 由于OpenVINO模型不提供时间戳，我们创建一个包含整个音频的segment
            segments = []
            if text.strip():
                # 计算音频总时长
                audio_duration = len(audio_array) / 16000.0  # 16000是采样率
                segments = [{
                    "start": 0.0,
                    "end": audio_duration,
                    "text": text.strip()
                }]
            
            # 返回与whisper兼容的格式
            return {
                "text": text,
                "segments": segments,
                "language": kwargs.get("language", "auto")
            }
            
        except Exception as e:
            raise RuntimeError(f"OpenVINO模型转录失败: {e}")


class IntelGPUPlugin(BaseModelLoaderPlugin):
    """Intel GPU优化模型加载器插件"""
    
    plugin_name = "intel_gpu"
    plugin_version = "1.0.0"
    
    def __init__(self, model_size: str, model_path: Optional[str] = None, **kwargs):
        super().__init__(model_size, model_path, **kwargs)
        self.intel_model_mapping = {
            "OpenVINO/whisper-tiny-fp16-ov": "OpenVINO_whisper-tiny-fp16-ov",
            "OpenVINO/whisper-base-fp16-ov": "OpenVINO_whisper-base-fp16-ov", 
            "OpenVINO/whisper-small-fp16-ov": "OpenVINO_whisper-small-fp16-ov",
            "OpenVINO/whisper-medium-fp16-ov": "OpenVINO_whisper-medium-fp16-ov",
            "OpenVINO/whisper-large-v3-fp16-ov": "OpenVINO_whisper-large-v3-fp16-ov"
        }
    
    @property
    def supported_models(self) -> List[str]:
        """支持的Intel GPU模型列表"""
        return list(self.intel_model_mapping.keys())
    
    def is_supported(self, model_size: str) -> bool:
        """检查是否为Intel GPU模型"""
        return model_size.startswith("OpenVINO/") and "fp16-ov" in model_size
    
    def validate_environment(self) -> bool:
        """验证运行环境"""
        try:
            from optimum.intel.openvino import OVModelForSpeechSeq2Seq
            from transformers import AutoProcessor
            import openvino as ov
            return True
        except ImportError:
            return False
    
    def get_requirements(self) -> List[str]:
        """获取依赖包列表"""
        return ["optimum[openvino]", "transformers", "openvino", "librosa"]
    
    def _find_optimized_model_path(self) -> Optional[Path]:
        """查找预下载的优化模型路径"""
        # 检查多个可能的目录
        model_dirs = [
            self.model_path,  # 插件系统使用的目录
            self.model_path.parent / "models"  # 旧的目录
        ]
        
        # 首先尝试精确匹配
        if self.model_size in self.intel_model_mapping:
            folder_name = self.intel_model_mapping[self.model_size]
            for models_dir in model_dirs:
                potential_path = models_dir / folder_name
                if potential_path.exists() and potential_path.is_dir():
                    return potential_path
        
        # 如果精确匹配失败，尝试模糊匹配
        for models_dir in model_dirs:
            if models_dir.exists():
                for model_dir in models_dir.glob("*"):
                    if model_dir.is_dir() and self.model_size in model_dir.name:
                        return model_dir
        
        return None
    
    def _validate_model_files(self, model_path: Path) -> bool:
        """验证模型文件完整性"""
        required_files = [
            "config.json",
            "openvino_encoder_model.xml",
            "openvino_decoder_model.xml"
        ]
        
        missing_files = [f for f in required_files if not (model_path / f).exists()]
        if missing_files:
            raise RuntimeError(f"Intel GPU模型文件不完整，缺少: {missing_files}")
        
        return True
    
    def _is_intel_gpu_available(self) -> bool:
        """检查Intel GPU是否可用"""
        try:
            import openvino as ov
            core = ov.Core()
            gpu_devices = [d for d in core.available_devices if "GPU" in d]
            return len(gpu_devices) > 0
        except Exception:
            return False
    
    def load(self):
        """加载Intel GPU优化模型"""
        if self._model is not None:
            return self._model
            
        print(f"使用Intel GPU插件加载模型: {self.model_size}")
        
        # 查找预下载的优化模型
        optimized_model_path = self._find_optimized_model_path()
        
        if not optimized_model_path:
            raise RuntimeError(f"未找到Intel GPU优化模型: {self.model_size}")
        
        print(f"找到预优化模型: {optimized_model_path}")
        
        # 验证模型文件完整性
        self._validate_model_files(optimized_model_path)
        
        try:
            from optimum.intel.openvino import OVModelForSpeechSeq2Seq
            from transformers import AutoProcessor
            
            print("正在加载OpenVINO优化模型...")
            
            # 加载模型（不编译）
            model = OVModelForSpeechSeq2Seq.from_pretrained(
                optimized_model_path,
                compile=False
            )
            
            # 编译到Intel GPU或CPU
            import openvino as ov
            core = ov.Core()
            gpu_devices = [d for d in core.available_devices if "GPU" in d]
            
            if gpu_devices:
                print(f"编译模型到Intel GPU: {gpu_devices[0]}")
                model.to(gpu_devices[0])
                model.compile()
            else:
                print("未检测到Intel GPU，使用CPU")
                model.to("CPU")
                model.compile()
            
            # 加载处理器
            processor = AutoProcessor.from_pretrained(optimized_model_path)
            
            # 创建包装器
            self._model = OpenVINOWhisperWrapper(model, processor)
            print("Intel GPU优化模型加载成功")
            return self._model
            
        except Exception as e:
            raise RuntimeError(f"Intel GPU模型加载失败: {e}")
    
    # 模型下载相关方法
    
    def get_downloadable_models(self) -> Dict[str, Dict[str, Any]]:
        """获取Intel GPU支持下载的模型列表"""
        return {
            "OpenVINO/whisper-tiny-fp16-ov": {
                "size": "39 MB",
                "description": "OpenVINO优化的tiny模型(FP16)",
                "download_urls": [
                    "https://huggingface.co/OpenVINO/whisper-tiny-fp16-ov/resolve/main/openvino_encoder_model.xml",
                    "https://huggingface.co/OpenVINO/whisper-tiny-fp16-ov/resolve/main/openvino_encoder_model.bin",
                    "https://huggingface.co/OpenVINO/whisper-tiny-fp16-ov/resolve/main/openvino_decoder_model.xml",
                    "https://huggingface.co/OpenVINO/whisper-tiny-fp16-ov/resolve/main/openvino_decoder_model.bin",
                    "https://huggingface.co/OpenVINO/whisper-tiny-fp16-ov/resolve/main/openvino_decoder_with_past_model.xml",
                    "https://huggingface.co/OpenVINO/whisper-tiny-fp16-ov/resolve/main/openvino_decoder_with_past_model.bin",
                    "https://huggingface.co/OpenVINO/whisper-tiny-fp16-ov/resolve/main/config.json",
                    "https://huggingface.co/OpenVINO/whisper-tiny-fp16-ov/resolve/main/tokenizer.json",
                    "https://huggingface.co/OpenVINO/whisper-tiny-fp16-ov/resolve/main/tokenizer_config.json",
                    "https://huggingface.co/OpenVINO/whisper-tiny-fp16-ov/resolve/main/preprocessor_config.json"
                ],
                "type": "OpenVINO优化",
                "language": "多语言",
                "accuracy": "较低",
                "speed": "最快"
            },
            "OpenVINO/whisper-base-fp16-ov": {
                "size": "74 MB",
                "description": "OpenVINO优化的base模型(FP16)",
                "download_urls": [
                    "https://huggingface.co/OpenVINO/whisper-base-fp16-ov/resolve/main/openvino_encoder_model.xml",
                    "https://huggingface.co/OpenVINO/whisper-base-fp16-ov/resolve/main/openvino_encoder_model.bin",
                    "https://huggingface.co/OpenVINO/whisper-base-fp16-ov/resolve/main/openvino_decoder_model.xml",
                    "https://huggingface.co/OpenVINO/whisper-base-fp16-ov/resolve/main/openvino_decoder_model.bin",
                    "https://huggingface.co/OpenVINO/whisper-base-fp16-ov/resolve/main/openvino_decoder_with_past_model.xml",
                    "https://huggingface.co/OpenVINO/whisper-base-fp16-ov/resolve/main/openvino_decoder_with_past_model.bin",
                    "https://huggingface.co/OpenVINO/whisper-base-fp16-ov/resolve/main/config.json",
                    "https://huggingface.co/OpenVINO/whisper-base-fp16-ov/resolve/main/tokenizer.json",
                    "https://huggingface.co/OpenVINO/whisper-base-fp16-ov/resolve/main/tokenizer_config.json",
                    "https://huggingface.co/OpenVINO/whisper-base-fp16-ov/resolve/main/preprocessor_config.json"
                ],
                "type": "OpenVINO优化",
                "language": "多语言",
                "accuracy": "中等",
                "speed": "快"
            },
            "OpenVINO/whisper-small-fp16-ov": {
                "size": "244 MB",
                "description": "OpenVINO优化的small模型(FP16)",
                "download_urls": [
                    "https://huggingface.co/OpenVINO/whisper-small-fp16-ov/resolve/main/openvino_encoder_model.xml",
                    "https://huggingface.co/OpenVINO/whisper-small-fp16-ov/resolve/main/openvino_encoder_model.bin",
                    "https://huggingface.co/OpenVINO/whisper-small-fp16-ov/resolve/main/openvino_decoder_model.xml",
                    "https://huggingface.co/OpenVINO/whisper-small-fp16-ov/resolve/main/openvino_decoder_model.bin",
                    "https://huggingface.co/OpenVINO/whisper-small-fp16-ov/resolve/main/openvino_decoder_with_past_model.xml",
                    "https://huggingface.co/OpenVINO/whisper-small-fp16-ov/resolve/main/openvino_decoder_with_past_model.bin",
                    "https://huggingface.co/OpenVINO/whisper-small-fp16-ov/resolve/main/config.json",
                    "https://huggingface.co/OpenVINO/whisper-small-fp16-ov/resolve/main/tokenizer.json",
                    "https://huggingface.co/OpenVINO/whisper-small-fp16-ov/resolve/main/tokenizer_config.json",
                    "https://huggingface.co/OpenVINO/whisper-small-fp16-ov/resolve/main/preprocessor_config.json"
                ],
                "type": "OpenVINO优化",
                "language": "多语言",
                "accuracy": "较好",
                "speed": "中等"
            },
            "OpenVINO/whisper-medium-fp16-ov": {
                "size": "769 MB",
                "description": "OpenVINO优化的medium模型(FP16)",
                "download_urls": [
                    "https://huggingface.co/OpenVINO/whisper-medium-fp16-ov/resolve/main/openvino_encoder_model.xml",
                    "https://huggingface.co/OpenVINO/whisper-medium-fp16-ov/resolve/main/openvino_encoder_model.bin",
                    "https://huggingface.co/OpenVINO/whisper-medium-fp16-ov/resolve/main/openvino_decoder_model.xml",
                    "https://huggingface.co/OpenVINO/whisper-medium-fp16-ov/resolve/main/openvino_decoder_model.bin",
                    "https://huggingface.co/OpenVINO/whisper-medium-fp16-ov/resolve/main/openvino_decoder_with_past_model.xml",
                    "https://huggingface.co/OpenVINO/whisper-medium-fp16-ov/resolve/main/openvino_decoder_with_past_model.bin",
                    "https://huggingface.co/OpenVINO/whisper-medium-fp16-ov/resolve/main/config.json",
                    "https://huggingface.co/OpenVINO/whisper-medium-fp16-ov/resolve/main/tokenizer.json",
                    "https://huggingface.co/OpenVINO/whisper-medium-fp16-ov/resolve/main/tokenizer_config.json",
                    "https://huggingface.co/OpenVINO/whisper-medium-fp16-ov/resolve/main/preprocessor_config.json"
                ],
                "type": "OpenVINO优化",
                "language": "多语言",
                "accuracy": "好",
                "speed": "较慢"
            },
            "OpenVINO/whisper-large-v3-fp16-ov": {
                "size": "1550 MB",
                "description": "OpenVINO优化的large-v3模型(FP16)",
                "download_urls": [
                    "https://huggingface.co/OpenVINO/whisper-large-v3-fp16-ov/resolve/main/openvino_encoder_model.xml",
                    "https://huggingface.co/OpenVINO/whisper-large-v3-fp16-ov/resolve/main/openvino_encoder_model.bin",
                    "https://huggingface.co/OpenVINO/whisper-large-v3-fp16-ov/resolve/main/openvino_decoder_model.xml",
                    "https://huggingface.co/OpenVINO/whisper-large-v3-fp16-ov/resolve/main/openvino_decoder_model.bin",
                    "https://huggingface.co/OpenVINO/whisper-large-v3-fp16-ov/resolve/main/openvino_decoder_with_past_model.xml",
                    "https://huggingface.co/OpenVINO/whisper-large-v3-fp16-ov/resolve/main/openvino_decoder_with_past_model.bin",
                    "https://huggingface.co/OpenVINO/whisper-large-v3-fp16-ov/resolve/main/config.json",
                    "https://huggingface.co/OpenVINO/whisper-large-v3-fp16-ov/resolve/main/tokenizer.json",
                    "https://huggingface.co/OpenVINO/whisper-large-v3-fp16-ov/resolve/main/tokenizer_config.json",
                    "https://huggingface.co/OpenVINO/whisper-large-v3-fp16-ov/resolve/main/preprocessor_config.json"
                ],
                "type": "OpenVINO优化",
                "language": "多语言",
                "accuracy": "最好",
                "speed": "慢"
            }
        }
    
    def is_model_downloaded(self, model_name: str) -> bool:
        """检查模型是否已下载"""
        if model_name not in self.intel_model_mapping:
            return False
        
        folder_name = self.intel_model_mapping[model_name]
        model_dir = self.model_path / folder_name
        
        # 检查必要的文件是否存在
        required_files = ["openvino_encoder_model.xml", "openvino_encoder_model.bin",
                         "openvino_decoder_model.xml", "openvino_decoder_model.bin",
                         "openvino_decoder_with_past_model.xml", "openvino_decoder_with_past_model.bin",
                         "config.json", "tokenizer.json"]
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
            # 获取模型目录
            folder_name = self.intel_model_mapping[model_name]
            model_dir = self.model_path / folder_name
            model_dir.mkdir(parents=True, exist_ok=True)
            
            # 需要下载的文件列表
            files_to_download = [
                "openvino_model.xml",
                "openvino_model.bin", 
                "config.json",
                "tokenizer.json",
                "tokenizer_config.json",
                "preprocessor_config.json"
            ]
            
            # 预下载验证：检查文件列表是否与Hugging Face实际文件匹配
            if progress_callback:
                progress_callback(model_name, 5, "验证文件列表...")
            
            validator = HuggingFaceValidator()
            base_url = f"https://huggingface.co/{model_name}/resolve/main"
            download_urls = [f"{base_url}/{filename}" for filename in files_to_download]
            
            is_valid, report = validator.validate_download_urls(model_name, download_urls)
            
            if not is_valid:
                print(f"\n警告: 模型 {model_name} 的文件列表与Hugging Face实际文件不匹配")
                validator.print_validation_report(report)
                
                # 获取修正后的文件列表
                corrected_files = validator.get_corrected_file_list(model_name, files_to_download)
                if corrected_files:
                    print(f"将使用修正后的文件列表进行下载...")
                    files_to_download = corrected_files
                else:
                    if progress_callback:
                        progress_callback(model_name, 0, "无法获取有效的文件列表")
                    return False
            
            total_files = len(files_to_download)
            for i, filename in enumerate(files_to_download):
                try:
                    if progress_callback:
                        progress_callback(model_name, int(10 + (i / total_files) * 85), f"下载 {filename}")
                    
                    url = f"{base_url}/{filename}"
                    success = self._download_file(url, model_dir / filename)
                    
                    if not success and filename in ["openvino_model.xml", "openvino_model.bin"]:
                        # 这些是必需文件
                        if progress_callback:
                            progress_callback(model_name, 0, f"下载必需文件失败: {filename}")
                        return False
                        
                except Exception as e:
                    if filename in ["openvino_model.xml", "openvino_model.bin"]:
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
            if model_name not in self.intel_model_mapping:
                return False
            
            folder_name = self.intel_model_mapping[model_name]
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
            if model_name not in self.intel_model_mapping:
                return "未知"
            
            folder_name = self.intel_model_mapping[model_name]
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