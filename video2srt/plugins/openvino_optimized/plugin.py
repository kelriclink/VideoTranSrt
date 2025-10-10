"""OpenVINO优化模型插件"""

import os
import librosa
import requests
import ssl
import urllib3
from pathlib import Path
from typing import List, Optional, Dict, Any, Callable
from ..base import BaseModelLoaderPlugin, ModelWrapper
from ...huggingface_validator import HuggingFaceValidator

# 禁用SSL警告
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
ssl._create_default_https_context = ssl._create_unverified_context


class OpenVINOWhisperWrapper(ModelWrapper):
    """OpenVINO Whisper模型包装器"""
    
    def __init__(self, model, processor):
        self.model = model
        self.processor = processor
    
    def transcribe(self, audio, **kwargs):
        """转录音频"""
        try:
            # 如果audio是文件路径，加载音频
            if isinstance(audio, (str, Path)):
                audio_data, sr = librosa.load(audio, sr=16000)
            else:
                audio_data = audio
                sr = kwargs.get("sr", 16000)
            
            # 预处理音频
            input_features = self.processor(
                audio_data, 
                sampling_rate=sr, 
                return_tensors="pt"
            ).input_features
            
            # 生成转录
            predicted_ids = self.model.generate(input_features)
            text = self.processor.batch_decode(predicted_ids, skip_special_tokens=True)[0]
            
            # 计算音频时长
            audio_duration = len(audio_data) / sr
            
            # 构建segments（简化版本）
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


class OpenVINOOptimizedPlugin(BaseModelLoaderPlugin):
    """OpenVINO优化模型加载器插件"""
    
    plugin_name = "openvino_optimized"
    plugin_version = "1.0.0"
    
    def __init__(self, model_size: str, model_path: Optional[str] = None, **kwargs):
        super().__init__(model_size, model_path, **kwargs)
        self.openvino_model_mapping = {
            "OpenVINO/whisper-tiny-fp16-ov": "OpenVINO_whisper-tiny-fp16-ov",
            "OpenVINO/whisper-base-fp16-ov": "OpenVINO_whisper-base-fp16-ov",
            "OpenVINO/whisper-small-fp16-ov": "OpenVINO_whisper-small-fp16-ov",
            "OpenVINO/whisper-medium-fp16-ov": "OpenVINO_whisper-medium-fp16-ov",
            "OpenVINO/whisper-large-fp16-ov": "OpenVINO_whisper-large-fp16-ov",
            "OpenVINO/whisper-large-v2-fp16-ov": "OpenVINO_whisper-large-v2-fp16-ov",
            "OpenVINO/whisper-large-v3-fp16-ov": "OpenVINO_whisper-large-v3-fp16-ov"
        }
    
    @property
    def supported_models(self) -> List[str]:
        """支持的OpenVINO模型列表"""
        return list(self.openvino_model_mapping.keys())
    
    def is_supported(self, model_size: str) -> bool:
        """检查是否为OpenVINO模型"""
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
        if self.model_size in self.openvino_model_mapping:
            folder_name = self.openvino_model_mapping[self.model_size]
            for models_dir in model_dirs:
                potential_path = models_dir / folder_name
                if potential_path.exists() and potential_path.is_dir():
                    return potential_path
        
        return None
    
    def _validate_model_files(self, model_path: Path) -> bool:
        """验证模型文件完整性"""
        required_files = [
            "openvino_encoder_model.xml",
            "openvino_encoder_model.bin",
            "openvino_decoder_model.xml",
            "openvino_decoder_model.bin",
            "openvino_decoder_with_past_model.xml",
            "openvino_decoder_with_past_model.bin",
            "config.json",
            "tokenizer.json"
        ]
        
        return all((model_path / file).exists() for file in required_files)
    
    def _is_openvino_available(self) -> bool:
        """检查OpenVINO是否可用"""
        try:
            import openvino as ov
            core = ov.Core()
            devices = core.available_devices
            return len(devices) > 0
        except:
            return True  # 默认假设可用
    
    def load(self):
        """加载OpenVINO模型"""
        if not self.validate_environment():
            raise RuntimeError("缺少必要的依赖包。请安装: pip install optimum[openvino] transformers openvino")
        
        # 查找模型路径
        model_path = self._find_optimized_model_path()
        if not model_path:
            raise FileNotFoundError(f"未找到模型 {self.model_size}。请先下载模型。")
        
        # 验证模型文件
        if not self._validate_model_files(model_path):
            raise FileNotFoundError(f"模型文件不完整: {model_path}")
        
        try:
            from optimum.intel.openvino import OVModelForSpeechSeq2Seq
            from transformers import AutoProcessor
            
            # 加载处理器
            processor = AutoProcessor.from_pretrained(str(model_path))
            
            # 加载模型
            model = OVModelForSpeechSeq2Seq.from_pretrained(
                str(model_path),
                device="CPU",  # 可以根据需要改为GPU
                compile=True
            )
            
            return OpenVINOWhisperWrapper(model, processor)
            
        except Exception as e:
            raise RuntimeError(f"加载OpenVINO模型失败: {e}")
    
    def get_downloadable_models(self) -> Dict[str, Dict[str, Any]]:
        """获取OpenVINO支持下载的模型列表"""
        return {
            "OpenVINO/whisper-tiny-fp16-ov": {
                "size": "150 MB",
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
                    "https://huggingface.co/OpenVINO/whisper-tiny-fp16-ov/resolve/main/special_tokens_map.json",
                    "https://huggingface.co/OpenVINO/whisper-tiny-fp16-ov/resolve/main/vocab.json",
                    "https://huggingface.co/OpenVINO/whisper-tiny-fp16-ov/resolve/main/merges.txt",
                    "https://huggingface.co/OpenVINO/whisper-tiny-fp16-ov/resolve/main/normalizer.json",
                    "https://huggingface.co/OpenVINO/whisper-tiny-fp16-ov/resolve/main/preprocessor_config.json",
                    "https://huggingface.co/OpenVINO/whisper-tiny-fp16-ov/resolve/main/generation_config.json",
                    "https://huggingface.co/OpenVINO/whisper-tiny-fp16-ov/resolve/main/openvino_tokenizer.xml",
                    "https://huggingface.co/OpenVINO/whisper-tiny-fp16-ov/resolve/main/openvino_tokenizer.bin"
                ],
                "type": "OpenVINO优化",
                "language": "多语言",
                "accuracy": "低",
                "speed": "很快"
            },
            "OpenVINO/whisper-base-fp16-ov": {
                "size": "290 MB",
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
                    "https://huggingface.co/OpenVINO/whisper-base-fp16-ov/resolve/main/special_tokens_map.json",
                    "https://huggingface.co/OpenVINO/whisper-base-fp16-ov/resolve/main/vocab.json",
                    "https://huggingface.co/OpenVINO/whisper-base-fp16-ov/resolve/main/merges.txt",
                    "https://huggingface.co/OpenVINO/whisper-base-fp16-ov/resolve/main/normalizer.json",
                    "https://huggingface.co/OpenVINO/whisper-base-fp16-ov/resolve/main/preprocessor_config.json",
                    "https://huggingface.co/OpenVINO/whisper-base-fp16-ov/resolve/main/generation_config.json",
                    "https://huggingface.co/OpenVINO/whisper-base-fp16-ov/resolve/main/openvino_tokenizer.xml",
                    "https://huggingface.co/OpenVINO/whisper-base-fp16-ov/resolve/main/openvino_tokenizer.bin"
                ],
                "type": "OpenVINO优化",
                "language": "多语言",
                "accuracy": "中等",
                "speed": "快"
            },
            "OpenVINO/whisper-small-fp16-ov": {
                "size": "970 MB",
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
                    "https://huggingface.co/OpenVINO/whisper-small-fp16-ov/resolve/main/special_tokens_map.json",
                    "https://huggingface.co/OpenVINO/whisper-small-fp16-ov/resolve/main/vocab.json",
                    "https://huggingface.co/OpenVINO/whisper-small-fp16-ov/resolve/main/merges.txt",
                    "https://huggingface.co/OpenVINO/whisper-small-fp16-ov/resolve/main/normalizer.json",
                    "https://huggingface.co/OpenVINO/whisper-small-fp16-ov/resolve/main/preprocessor_config.json",
                    "https://huggingface.co/OpenVINO/whisper-small-fp16-ov/resolve/main/generation_config.json",
                    "https://huggingface.co/OpenVINO/whisper-small-fp16-ov/resolve/main/openvino_tokenizer.xml",
                    "https://huggingface.co/OpenVINO/whisper-small-fp16-ov/resolve/main/openvino_tokenizer.bin"
                ],
                "type": "OpenVINO优化",
                "language": "多语言",
                "accuracy": "中等",
                "speed": "快"
            },
            "OpenVINO/whisper-medium-fp16-ov": {
                "size": "1.5 GB",
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
                    "https://huggingface.co/OpenVINO/whisper-medium-fp16-ov/resolve/main/special_tokens_map.json",
                    "https://huggingface.co/OpenVINO/whisper-medium-fp16-ov/resolve/main/vocab.json",
                    "https://huggingface.co/OpenVINO/whisper-medium-fp16-ov/resolve/main/merges.txt",
                    "https://huggingface.co/OpenVINO/whisper-medium-fp16-ov/resolve/main/normalizer.json",
                    "https://huggingface.co/OpenVINO/whisper-medium-fp16-ov/resolve/main/preprocessor_config.json",
                    "https://huggingface.co/OpenVINO/whisper-medium-fp16-ov/resolve/main/generation_config.json",
                    "https://huggingface.co/OpenVINO/whisper-medium-fp16-ov/resolve/main/openvino_tokenizer.xml",
                    "https://huggingface.co/OpenVINO/whisper-medium-fp16-ov/resolve/main/openvino_tokenizer.bin"
                ],
                "type": "OpenVINO优化",
                "language": "多语言",
                "accuracy": "高",
                "speed": "中等"
            },
            "OpenVINO/whisper-large-fp16-ov": {
                "size": "3.1 GB",
                "description": "OpenVINO优化的large模型(FP16)",
                "download_urls": [
                    "https://huggingface.co/OpenVINO/whisper-large-fp16-ov/resolve/main/openvino_encoder_model.xml",
                    "https://huggingface.co/OpenVINO/whisper-large-fp16-ov/resolve/main/openvino_encoder_model.bin",
                    "https://huggingface.co/OpenVINO/whisper-large-fp16-ov/resolve/main/openvino_decoder_model.xml",
                    "https://huggingface.co/OpenVINO/whisper-large-fp16-ov/resolve/main/openvino_decoder_model.bin",
                    "https://huggingface.co/OpenVINO/whisper-large-fp16-ov/resolve/main/openvino_decoder_with_past_model.xml",
                    "https://huggingface.co/OpenVINO/whisper-large-fp16-ov/resolve/main/openvino_decoder_with_past_model.bin",
                    "https://huggingface.co/OpenVINO/whisper-large-fp16-ov/resolve/main/config.json",
                    "https://huggingface.co/OpenVINO/whisper-large-fp16-ov/resolve/main/tokenizer.json",
                    "https://huggingface.co/OpenVINO/whisper-large-fp16-ov/resolve/main/tokenizer_config.json",
                    "https://huggingface.co/OpenVINO/whisper-large-fp16-ov/resolve/main/special_tokens_map.json",
                    "https://huggingface.co/OpenVINO/whisper-large-fp16-ov/resolve/main/vocab.json",
                    "https://huggingface.co/OpenVINO/whisper-large-fp16-ov/resolve/main/merges.txt",
                    "https://huggingface.co/OpenVINO/whisper-large-fp16-ov/resolve/main/normalizer.json",
                    "https://huggingface.co/OpenVINO/whisper-large-fp16-ov/resolve/main/preprocessor_config.json",
                    "https://huggingface.co/OpenVINO/whisper-large-fp16-ov/resolve/main/generation_config.json",
                    "https://huggingface.co/OpenVINO/whisper-large-fp16-ov/resolve/main/openvino_tokenizer.xml",
                    "https://huggingface.co/OpenVINO/whisper-large-fp16-ov/resolve/main/openvino_tokenizer.bin"
                ],
                "type": "OpenVINO优化",
                "language": "多语言",
                "accuracy": "高",
                "speed": "中等"
            },
            "OpenVINO/whisper-large-v2-fp16-ov": {
                "size": "3.1 GB",
                "description": "OpenVINO优化的large-v2模型(FP16)",
                "download_urls": [
                    "https://huggingface.co/OpenVINO/whisper-large-v2-fp16-ov/resolve/main/openvino_encoder_model.xml",
                    "https://huggingface.co/OpenVINO/whisper-large-v2-fp16-ov/resolve/main/openvino_encoder_model.bin",
                    "https://huggingface.co/OpenVINO/whisper-large-v2-fp16-ov/resolve/main/openvino_decoder_model.xml",
                    "https://huggingface.co/OpenVINO/whisper-large-v2-fp16-ov/resolve/main/openvino_decoder_model.bin",
                    "https://huggingface.co/OpenVINO/whisper-large-v2-fp16-ov/resolve/main/openvino_decoder_with_past_model.xml",
                    "https://huggingface.co/OpenVINO/whisper-large-v2-fp16-ov/resolve/main/openvino_decoder_with_past_model.bin",
                    "https://huggingface.co/OpenVINO/whisper-large-v2-fp16-ov/resolve/main/config.json",
                    "https://huggingface.co/OpenVINO/whisper-large-v2-fp16-ov/resolve/main/tokenizer.json",
                    "https://huggingface.co/OpenVINO/whisper-large-v2-fp16-ov/resolve/main/tokenizer_config.json",
                    "https://huggingface.co/OpenVINO/whisper-large-v2-fp16-ov/resolve/main/special_tokens_map.json",
                    "https://huggingface.co/OpenVINO/whisper-large-v2-fp16-ov/resolve/main/vocab.json",
                    "https://huggingface.co/OpenVINO/whisper-large-v2-fp16-ov/resolve/main/merges.txt",
                    "https://huggingface.co/OpenVINO/whisper-large-v2-fp16-ov/resolve/main/normalizer.json",
                    "https://huggingface.co/OpenVINO/whisper-large-v2-fp16-ov/resolve/main/preprocessor_config.json",
                    "https://huggingface.co/OpenVINO/whisper-large-v2-fp16-ov/resolve/main/generation_config.json",
                    "https://huggingface.co/OpenVINO/whisper-large-v2-fp16-ov/resolve/main/openvino_tokenizer.xml",
                    "https://huggingface.co/OpenVINO/whisper-large-v2-fp16-ov/resolve/main/openvino_tokenizer.bin"
                ],
                "type": "OpenVINO优化",
                "language": "多语言",
                "accuracy": "高",
                "speed": "中等"
            },
            "OpenVINO/whisper-large-v3-fp16-ov": {
                "size": "3.1 GB",
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
                    "https://huggingface.co/OpenVINO/whisper-large-v3-fp16-ov/resolve/main/special_tokens_map.json",
                    "https://huggingface.co/OpenVINO/whisper-large-v3-fp16-ov/resolve/main/vocab.json",
                    "https://huggingface.co/OpenVINO/whisper-large-v3-fp16-ov/resolve/main/merges.txt",
                    "https://huggingface.co/OpenVINO/whisper-large-v3-fp16-ov/resolve/main/normalizer.json",
                    "https://huggingface.co/OpenVINO/whisper-large-v3-fp16-ov/resolve/main/preprocessor_config.json",
                    "https://huggingface.co/OpenVINO/whisper-large-v3-fp16-ov/resolve/main/generation_config.json",
                    "https://huggingface.co/OpenVINO/whisper-large-v3-fp16-ov/resolve/main/openvino_tokenizer.xml",
                    "https://huggingface.co/OpenVINO/whisper-large-v3-fp16-ov/resolve/main/openvino_tokenizer.bin"
                ],
                "type": "OpenVINO优化",
                "language": "多语言",
                "accuracy": "高",
                "speed": "中等"
            }
        }
    
    def is_model_downloaded(self, model_name: str) -> bool:
        """检查模型是否已下载"""
        folder_name = model_name.replace("/", "_")
        model_dir = self.model_path / folder_name
        
        # 检查必要的文件是否存在
        required_files = [
            "openvino_encoder_model.xml",
            "openvino_encoder_model.bin",
            "openvino_decoder_model.xml",
            "openvino_decoder_model.bin",
            "openvino_decoder_with_past_model.xml",
            "openvino_decoder_with_past_model.bin",
            "config.json",
            "tokenizer.json",
            "tokenizer_config.json",
            "special_tokens_map.json",
            "vocab.json",
            "merges.txt",
            "normalizer.json",
            "preprocessor_config.json",
            "generation_config.json",
            "openvino_tokenizer.xml",
            "openvino_tokenizer.bin"
        ]
        return all((model_dir / file).exists() for file in required_files)
    
    def download_model(self, model_name: str, progress_callback: Optional[Callable] = None) -> bool:
        """下载模型"""
        if model_name not in self.get_downloadable_models():
            raise ValueError(f"不支持的模型: {model_name}")
        
        model_info = self.get_downloadable_models()[model_name]
        folder_name = model_name.replace("/", "_")
        model_dir = self.model_path / folder_name
        
        # 创建模型目录
        model_dir.mkdir(parents=True, exist_ok=True)
        
        try:
            download_urls = model_info["download_urls"]
            
            # 预下载验证：检查文件列表是否与Hugging Face实际文件匹配
            if progress_callback:
                progress_callback(f"验证文件列表...")
            
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
                        progress_callback("无法获取有效的文件列表")
                    return False
            
            total_files = len(download_urls)
            for i, url in enumerate(download_urls):
                file_name = url.split("/")[-1]
                file_path = model_dir / file_name
                
                if progress_callback:
                    progress_callback(f"下载文件 {i+1}/{total_files}: {file_name}")
                
                if not self._download_file(url, file_path):
                    return False
            
            return True
            
        except Exception as e:
            print(f"下载模型失败: {e}")
            return False
    
    def _download_file(self, url: str, file_path: Path) -> bool:
        """下载单个文件"""
        try:
            response = requests.get(url, stream=True, verify=False)
            response.raise_for_status()
            
            with open(file_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            return True
        except Exception as e:
            print(f"下载文件失败 {url}: {e}")
            return False
    
    def delete_model(self, model_name: str) -> bool:
        """删除模型"""
        folder_name = model_name.replace("/", "_")
        model_dir = self.model_path / folder_name
        
        if model_dir.exists():
            try:
                import shutil
                shutil.rmtree(model_dir)
                return True
            except Exception as e:
                print(f"删除模型失败: {e}")
                return False
        return True
    
    def get_model_file_size(self, model_name: str) -> str:
        """获取模型文件大小"""
        if model_name in self.get_downloadable_models():
            return self.get_downloadable_models()[model_name]["size"]
        else:
            return "未知"