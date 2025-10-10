"""
语音识别模块
使用 OpenAI Whisper 进行语音转文字
"""

import whisper
from pathlib import Path
from typing import List, Dict, Any, Optional
import torch
import os

from .models import Segment, TranscriptionResult
from .config_manager import config_manager


class Transcriber:
    """语音识别器"""
    
    def __init__(self, model_size: str = "base", model_path: Optional[str] = None):
        """
        初始化识别器
        
        Args:
            model_size: 模型大小 (tiny, base, small, medium, large)
            model_path: 本地模型路径，如果为None则使用默认路径
        """
        self.model_size = model_size
        self.model = None
        self.device = self._determine_device()
        
        # 设置模型路径
        if model_path:
            self.model_path = Path(model_path)
        else:
            # 使用项目目录下的model文件夹
            project_root = Path(__file__).parent.parent
            self.model_path = project_root / "model"
            self.model_path.mkdir(exist_ok=True)
    
    def _determine_device(self) -> str:
        """
        根据配置和硬件情况确定使用的设备
        
        Returns:
            设备名称: 'cpu', 'cuda', 'openvino' 等
        """
        device_config = config_manager.get_whisper_device()
        
        if device_config == 'auto':
            # 自动选择设备：优先CUDA，其次CPU
            return 'cuda' if torch.cuda.is_available() else 'cpu'
        
        # 仅允许 'cpu' 或 'cuda'，其他值回退为 'cpu'
        if device_config in ('cpu', 'cuda'):
            return device_config
        
        return 'cpu'
    
    
    def load_model(self):
        """加载 Whisper 模型"""
        if self.model is None:
            print(f"正在加载 Whisper 模型: {self.model_size}")
            
            try:
                from .model_loaders import ModelLoaderFactory
                
                # 使用插件化的工厂模式创建合适的加载器
                loader = ModelLoaderFactory.create_loader(
                    model_size=self.model_size,
                    model_path=str(self.model_path),
                    device=self.device
                )
                
                # 加载模型
                self.model = loader.load()
                
                print(f"模型加载完成，使用设备: {self.device}")
                print(f"模型存储路径: {self.model_path}")
                
            except Exception as e:
                print(f"模型加载失败: {e}")
                print("可能的解决方案:")
                print("1. 检查网络连接")
                print("2. 设置环境变量: set PYTHONHTTPSVERIFY=0")
                print("3. 使用离线模式或手动下载模型")
                print(f"4. 检查模型路径: {self.model_path}")
                # 已移除 Intel GPU/OpenVINO 相关提示
                raise RuntimeError(f"无法加载 Whisper 模型: {e}")
    
    def get_model_info(self) -> Dict[str, Any]:
        """获取模型信息"""
        return {
            "model_size": self.model_size,
            "model_path": str(self.model_path),
            "device": self.device,
            "is_loaded": self.model is not None
        }
    
    def list_available_models(self) -> List[str]:
        """列出可用的模型大小"""
        return ["tiny.en", "base.en", "small.en", "medium.en", 
                "tiny", "base", "small", "medium", "large"]
    
    def check_model_exists(self, model_size: str = None) -> bool:
        """检查指定模型是否已下载"""
        if model_size is None:
            model_size = self.model_size
        
        # Whisper 模型文件通常以 .pt 结尾
        model_file = self.model_path / f"{model_size}.pt"
        return model_file.exists()
    
    def get_model_size_info(self) -> Dict[str, Dict[str, Any]]:
        """获取各模型大小的详细信息"""
        return {
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
    
    def transcribe(self, audio_path: Path, language: Optional[str] = None) -> TranscriptionResult:
        """
        转录音频文件
        
        Args:
            audio_path: 音频文件路径
            language: 语言代码，None 表示自动检测
            
        Returns:
            TranscriptionResult 对象
        """
        if self.model is None:
            self.load_model()
        
        audio_path = Path(audio_path)
        if not audio_path.exists():
            raise FileNotFoundError(f"音频文件不存在: {audio_path}")
        
        print(f"开始转录: {audio_path}")
        
        # 执行转录
        whisper_result = self.model.transcribe(
            str(audio_path),
            language=language,
            verbose=True
        )
        
        print("转录完成")
        
        # 转换为结构化结果
        return TranscriptionResult.from_whisper_result(whisper_result, self.model_size)
    
    def get_segments(self, result: TranscriptionResult) -> List[Segment]:
        """
        从转录结果中提取分段信息
        
        Args:
            result: TranscriptionResult 对象
            
        Returns:
            Segment 对象列表
        """
        return result.segments
    
    def get_full_text(self, result: TranscriptionResult) -> str:
        """
        获取完整转录文本
        
        Args:
            result: TranscriptionResult 对象
            
        Returns:
            完整文本
        """
        return result.text
    
    def get_language(self, result: TranscriptionResult) -> str:
        """
        获取检测到的语言
        
        Args:
            result: TranscriptionResult 对象
            
        Returns:
            语言代码
        """
        return result.language
    
    def is_english_model(self, model_size: str = None) -> bool:
        """检查是否为英语专用模型"""
        if model_size is None:
            model_size = self.model_size
        return model_size.endswith('.en')
    
    def get_english_models(self) -> List[str]:
        """获取英语专用模型列表"""
        return ["tiny.en", "base.en", "small.en", "medium.en"]
    
    def get_multilingual_models(self) -> List[str]:
        """获取多语言模型列表"""
        return ["tiny", "base", "small", "medium", "large"]
    
    def get_model_type(self, model_size: str = None) -> str:
        """获取模型类型"""
        if model_size is None:
            model_size = self.model_size
        
        if model_size.endswith('.en'):
            return "英语专用"
        else:
            return "多语言"
