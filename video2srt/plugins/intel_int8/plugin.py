"""Intel INT8 优化模型插件"""

import os
import librosa
import requests
import ssl
import urllib3
from pathlib import Path
from typing import List, Optional, Dict, Any, Callable
from ..base import BaseModelLoaderPlugin, ModelWrapper

# 禁用SSL警告
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
ssl._create_default_https_context = ssl._create_unverified_context


class IntelINT8WhisperWrapper(ModelWrapper):
    """Intel INT8 Whisper模型包装器"""
    
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
            raise RuntimeError(f"Intel INT8模型转录失败: {e}")


class IntelINT8Plugin(BaseModelLoaderPlugin):
    """Intel INT8优化模型加载器插件"""
    
    plugin_name = "intel_int8"
    plugin_version = "1.0.0"
    
    def __init__(self, model_size: str, model_path: Optional[str] = None, **kwargs):
        super().__init__(model_size, model_path, **kwargs)
        self.intel_model_mapping = {
            "Intel/whisper-large-v2-int8-static-inc": "Intel_whisper-large-v2-int8-static-inc",
            "Intel/whisper-large-int8-static-inc": "Intel_whisper-large-int8-static-inc",
            "Intel/whisper-large-int8-dynamic-inc": "Intel_whisper-large-int8-dynamic-inc",
            "Intel/whisper-base-int8-static-inc": "Intel_whisper-base-int8-static-inc"
        }
    
    @property
    def supported_models(self) -> List[str]:
        """支持的Intel INT8模型列表"""
        return list(self.intel_model_mapping.keys())
    
    def is_supported(self, model_size: str) -> bool:
        """检查是否为Intel INT8模型"""
        return model_size.startswith("Intel/") and "int8" in model_size
    
    def validate_environment(self) -> bool:
        """验证运行环境"""
        try:
            from optimum.onnxruntime import ORTModelForSpeechSeq2Seq
            from transformers import AutoProcessor
            import onnxruntime as ort
            return True
        except ImportError:
            return False
    
    def get_requirements(self) -> List[str]:
        """获取依赖包列表"""
        return ["optimum[onnxruntime]", "transformers", "onnxruntime", "librosa"]
    
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
        
        return None
    
    def _validate_model_files(self, model_path: Path) -> bool:
        """验证模型文件完整性"""
        required_files = [
            "encoder_model.onnx",
            "decoder_model.onnx", 
            "decoder_model_merged.onnx",
            "config.json",
            "tokenizer.json"
        ]
        
        return all((model_path / file).exists() for file in required_files)
    
    def _is_intel_hardware_available(self) -> bool:
        """检查是否有Intel硬件可用"""
        try:
            import onnxruntime as ort
            providers = ort.get_available_providers()
            # 检查是否有Intel相关的执行提供者
            intel_providers = [p for p in providers if 'Intel' in p or 'CPU' in p]
            return len(intel_providers) > 0
        except:
            return True  # 默认假设可用
    
    def load(self):
        """加载Intel INT8模型"""
        if not self.validate_environment():
            raise RuntimeError("缺少必要的依赖包。请安装: pip install optimum[onnxruntime] transformers onnxruntime")
        
        # 查找模型路径
        model_path = self._find_optimized_model_path()
        if not model_path:
            raise FileNotFoundError(f"未找到模型 {self.model_size}。请先下载模型。")
        
        # 验证模型文件
        if not self._validate_model_files(model_path):
            raise FileNotFoundError(f"模型文件不完整: {model_path}")
        
        try:
            from optimum.onnxruntime import ORTModelForSpeechSeq2Seq
            from transformers import AutoProcessor
            
            # 加载处理器
            processor = AutoProcessor.from_pretrained(str(model_path))
            
            # 配置ONNX Runtime会话选项
            session_options = {
                "providers": ["CPUExecutionProvider"],  # 使用CPU执行提供者
                "provider_options": [{"use_arena": False}]  # 优化内存使用
            }
            
            # 加载模型
            model = ORTModelForSpeechSeq2Seq.from_pretrained(
                str(model_path),
                **session_options
            )
            
            return IntelINT8WhisperWrapper(model, processor)
            
        except Exception as e:
            raise RuntimeError(f"加载Intel INT8模型失败: {e}")
    
    def get_downloadable_models(self) -> Dict[str, Dict[str, Any]]:
        """获取Intel INT8支持下载的模型列表"""
        return {
            "Intel/whisper-large-v2-int8-static-inc": {
                "size": "2.8 GB",
                "description": "Intel INT8优化的large-v2模型(静态量化)",
                "download_urls": [
                    "https://huggingface.co/Intel/whisper-large-v2-int8-static-inc/resolve/main/config.json",
                    "https://huggingface.co/Intel/whisper-large-v2-int8-static-inc/resolve/main/generation_config.json",
                    "https://huggingface.co/Intel/whisper-large-v2-int8-static-inc/resolve/main/preprocessor_config.json",
                    "https://huggingface.co/Intel/whisper-large-v2-int8-static-inc/resolve/main/tokenizer.json",
                    "https://huggingface.co/Intel/whisper-large-v2-int8-static-inc/resolve/main/tokenizer_config.json",
                    "https://huggingface.co/Intel/whisper-large-v2-int8-static-inc/resolve/main/vocab.json",
                    "https://huggingface.co/Intel/whisper-large-v2-int8-static-inc/resolve/main/merges.txt",
                    "https://huggingface.co/Intel/whisper-large-v2-int8-static-inc/resolve/main/normalizer.json",
                    "https://huggingface.co/Intel/whisper-large-v2-int8-static-inc/resolve/main/added_tokens.json",
                    "https://huggingface.co/Intel/whisper-large-v2-int8-static-inc/resolve/main/special_tokens_map.json",
                    "https://huggingface.co/Intel/whisper-large-v2-int8-static-inc/resolve/main/encoder_model.onnx",
                    "https://huggingface.co/Intel/whisper-large-v2-int8-static-inc/resolve/main/decoder_model.onnx",
                    "https://huggingface.co/Intel/whisper-large-v2-int8-static-inc/resolve/main/decoder_with_past_model.onnx"
                ],
                "type": "Intel INT8优化",
                "language": "多语言",
                "accuracy": "高",
                "speed": "快"
            },
            "Intel/whisper-large-int8-static-inc": {
                "size": "2.4 GB",
                "description": "Intel INT8优化的large模型(静态量化)",
                "download_urls": [
                    "https://huggingface.co/Intel/whisper-large-int8-static-inc/resolve/main/config.json",
                    "https://huggingface.co/Intel/whisper-large-int8-static-inc/resolve/main/generation_config.json",
                    "https://huggingface.co/Intel/whisper-large-int8-static-inc/resolve/main/preprocessor_config.json",
                    "https://huggingface.co/Intel/whisper-large-int8-static-inc/resolve/main/tokenizer.json",
                    "https://huggingface.co/Intel/whisper-large-int8-static-inc/resolve/main/tokenizer_config.json",
                    "https://huggingface.co/Intel/whisper-large-int8-static-inc/resolve/main/vocab.json",
                    "https://huggingface.co/Intel/whisper-large-int8-static-inc/resolve/main/merges.txt",
                    "https://huggingface.co/Intel/whisper-large-int8-static-inc/resolve/main/normalizer.json",
                    "https://huggingface.co/Intel/whisper-large-int8-static-inc/resolve/main/added_tokens.json",
                    "https://huggingface.co/Intel/whisper-large-int8-static-inc/resolve/main/special_tokens_map.json",
                    "https://huggingface.co/Intel/whisper-large-int8-static-inc/resolve/main/encoder_model.onnx",
                    "https://huggingface.co/Intel/whisper-large-int8-static-inc/resolve/main/decoder_model.onnx",
                    "https://huggingface.co/Intel/whisper-large-int8-static-inc/resolve/main/decoder_with_past_model.onnx"
                ],
                "type": "Intel INT8优化",
                "language": "多语言",
                "accuracy": "高",
                "speed": "快"
            },
            "Intel/whisper-large-int8-dynamic-inc": {
                "size": "2.4 GB",
                "description": "Intel INT8优化的large模型(动态量化)",
                "download_urls": [
                    "https://huggingface.co/Intel/whisper-large-int8-dynamic-inc/resolve/main/config.json",
                    "https://huggingface.co/Intel/whisper-large-int8-dynamic-inc/resolve/main/generation_config.json",
                    "https://huggingface.co/Intel/whisper-large-int8-dynamic-inc/resolve/main/preprocessor_config.json",
                    "https://huggingface.co/Intel/whisper-large-int8-dynamic-inc/resolve/main/tokenizer.json",
                    "https://huggingface.co/Intel/whisper-large-int8-dynamic-inc/resolve/main/tokenizer_config.json",
                    "https://huggingface.co/Intel/whisper-large-int8-dynamic-inc/resolve/main/vocab.json",
                    "https://huggingface.co/Intel/whisper-large-int8-dynamic-inc/resolve/main/merges.txt",
                    "https://huggingface.co/Intel/whisper-large-int8-dynamic-inc/resolve/main/normalizer.json",
                    "https://huggingface.co/Intel/whisper-large-int8-dynamic-inc/resolve/main/added_tokens.json",
                    "https://huggingface.co/Intel/whisper-large-int8-dynamic-inc/resolve/main/special_tokens_map.json",
                    "https://huggingface.co/Intel/whisper-large-int8-dynamic-inc/resolve/main/encoder_model.onnx",
                    "https://huggingface.co/Intel/whisper-large-int8-dynamic-inc/resolve/main/decoder_model.onnx",
                    "https://huggingface.co/Intel/whisper-large-int8-dynamic-inc/resolve/main/decoder_with_past_model.onnx"
                ],
                "type": "Intel INT8优化",
                "language": "多语言",
                "accuracy": "高",
                "speed": "快"
            },
            "Intel/whisper-base-int8-static-inc": {
                "size": "0.32 GB",
                "description": "Intel INT8优化的base模型(静态量化)",
                "download_urls": [
                    "https://huggingface.co/Intel/whisper-base-int8-static-inc/resolve/main/config.json",
                    "https://huggingface.co/Intel/whisper-base-int8-static-inc/resolve/main/generation_config.json",
                    "https://huggingface.co/Intel/whisper-base-int8-static-inc/resolve/main/preprocessor_config.json",
                    "https://huggingface.co/Intel/whisper-base-int8-static-inc/resolve/main/tokenizer.json",
                    "https://huggingface.co/Intel/whisper-base-int8-static-inc/resolve/main/tokenizer_config.json",
                    "https://huggingface.co/Intel/whisper-base-int8-static-inc/resolve/main/vocab.json",
                    "https://huggingface.co/Intel/whisper-base-int8-static-inc/resolve/main/merges.txt",
                    "https://huggingface.co/Intel/whisper-base-int8-static-inc/resolve/main/normalizer.json",
                    "https://huggingface.co/Intel/whisper-base-int8-static-inc/resolve/main/added_tokens.json",
                    "https://huggingface.co/Intel/whisper-base-int8-static-inc/resolve/main/special_tokens_map.json",
                    "https://huggingface.co/Intel/whisper-base-int8-static-inc/resolve/main/encoder_model.onnx",
                    "https://huggingface.co/Intel/whisper-base-int8-static-inc/resolve/main/decoder_model.onnx",
                    "https://huggingface.co/Intel/whisper-base-int8-static-inc/resolve/main/decoder_with_past_model.onnx"
                ],
                "type": "Intel INT8优化",
                "language": "多语言",
                "accuracy": "中等",
                "speed": "很快"
            },
            "Intel/whisper-medium-int8-static-inc": {
                "size": "1.6 GB",
                "description": "Intel INT8优化的medium模型(静态量化)",
                "download_urls": [
                    "https://huggingface.co/Intel/whisper-medium-int8-static-inc/resolve/main/config.json",
                    "https://huggingface.co/Intel/whisper-medium-int8-static-inc/resolve/main/generation_config.json",
                    "https://huggingface.co/Intel/whisper-medium-int8-static-inc/resolve/main/preprocessor_config.json",
                    "https://huggingface.co/Intel/whisper-medium-int8-static-inc/resolve/main/tokenizer.json",
                    "https://huggingface.co/Intel/whisper-medium-int8-static-inc/resolve/main/tokenizer_config.json",
                    "https://huggingface.co/Intel/whisper-medium-int8-static-inc/resolve/main/vocab.json",
                    "https://huggingface.co/Intel/whisper-medium-int8-static-inc/resolve/main/merges.txt",
                    "https://huggingface.co/Intel/whisper-medium-int8-static-inc/resolve/main/normalizer.json",
                    "https://huggingface.co/Intel/whisper-medium-int8-static-inc/resolve/main/added_tokens.json",
                    "https://huggingface.co/Intel/whisper-medium-int8-static-inc/resolve/main/special_tokens_map.json",
                    "https://huggingface.co/Intel/whisper-medium-int8-static-inc/resolve/main/encoder_model.onnx",
                    "https://huggingface.co/Intel/whisper-medium-int8-static-inc/resolve/main/decoder_model.onnx",
                    "https://huggingface.co/Intel/whisper-medium-int8-static-inc/resolve/main/decoder_with_past_model.onnx"
                ],
                "type": "Intel INT8优化",
                "language": "多语言",
                "accuracy": "高",
                "speed": "快"
            }
        }
    
    def is_model_downloaded(self, model_name: str) -> bool:
        """检查模型是否已下载"""
        folder_name = model_name.replace("/", "_")
        model_dir = self.model_path / folder_name
        
        # 检查必要的文件是否存在
        required_files = ["encoder_model.onnx", "decoder_model.onnx", 
                         "decoder_with_past_model.onnx", "config.json", "tokenizer.json"]
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
            total_files = len(model_info["download_urls"])
            for i, url in enumerate(model_info["download_urls"]):
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