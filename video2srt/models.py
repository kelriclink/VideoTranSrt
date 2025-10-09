"""
数据模型定义
定义项目中使用的数据结构
"""

from dataclasses import dataclass
from typing import Optional, List, Dict, Any
from pathlib import Path


@dataclass
class Segment:
    """字幕段数据类"""
    start: float  # 开始时间（秒）
    end: float    # 结束时间（秒）
    text: str     # 文本内容
    language: Optional[str] = None  # 语言代码
    confidence: Optional[float] = None  # 置信度
    
    def __post_init__(self):
        """数据验证"""
        if self.start < 0:
            raise ValueError("开始时间不能为负数")
        if self.end < self.start:
            raise ValueError("结束时间不能早于开始时间")
        if not self.text.strip():
            raise ValueError("文本内容不能为空")
    
    @property
    def duration(self) -> float:
        """获取时长"""
        return self.end - self.start
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式（向后兼容）"""
        result = {
            "start": self.start,
            "end": self.end,
            "text": self.text
        }
        if self.language:
            result["language"] = self.language
        if self.confidence is not None:
            result["confidence"] = self.confidence
        return result
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Segment':
        """从字典创建Segment"""
        return cls(
            start=data["start"],
            end=data["end"],
            text=data["text"],
            language=data.get("language"),
            confidence=data.get("confidence")
        )
    
    @classmethod
    def from_whisper_segment(cls, whisper_segment: Dict[str, Any]) -> 'Segment':
        """从Whisper输出创建Segment"""
        return cls(
            start=whisper_segment["start"],
            end=whisper_segment["end"],
            text=whisper_segment["text"].strip(),
            confidence=whisper_segment.get("confidence")
        )


@dataclass
class TranscriptionResult:
    """转录结果数据类"""
    segments: List[Segment]
    language: str
    text: str  # 完整文本
    duration: float  # 总时长
    model_name: str  # 使用的模型名称
    
    @classmethod
    def from_whisper_result(cls, whisper_result: Dict[str, Any], model_name: str) -> 'TranscriptionResult':
        """从Whisper结果创建TranscriptionResult"""
        segments = [Segment.from_whisper_segment(seg) for seg in whisper_result.get("segments", [])]
        
        return cls(
            segments=segments,
            language=whisper_result.get("language", "unknown"),
            text=whisper_result.get("text", ""),
            duration=segments[-1].end if segments else 0.0,
            model_name=model_name
        )


@dataclass
class TranslationResult:
    """翻译结果数据类"""
    segments: List[Segment]
    source_language: str
    target_language: str
    translator_name: str
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "segments": [seg.to_dict() for seg in self.segments],
            "source_language": self.source_language,
            "target_language": self.target_language,
            "translator_name": self.translator_name
        }


@dataclass
class ProcessingConfig:
    """处理配置数据类"""
    input_path: Path
    output_path: Optional[Path] = None
    model_size: str = "base"
    language: Optional[str] = None  # 源语言
    translate_to: Optional[str] = None  # 目标语言
    bilingual: bool = False
    translator_type: str = "google"
    device: str = "auto"  # cpu, cuda, auto
    
    def __post_init__(self):
        """数据验证和处理"""
        self.input_path = Path(self.input_path)
        if self.output_path:
            self.output_path = Path(self.output_path)
        else:
            self.output_path = self.input_path.with_suffix('.srt')


@dataclass
class ProcessingResult:
    """处理结果数据类"""
    success: bool
    output_path: Optional[Path]
    transcription: Optional[TranscriptionResult]
    translation: Optional[TranslationResult]
    error_message: Optional[str] = None
    processing_time: Optional[float] = None  # 处理耗时（秒）
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式，便于序列化"""
        result = {
            "success": self.success,
            "output_path": str(self.output_path) if self.output_path else None,
            "error_message": self.error_message,
            "processing_time": self.processing_time
        }
        
        if self.transcription:
            result["transcription"] = {
                "language": self.transcription.language,
                "text": self.transcription.text,
                "duration": self.transcription.duration,
                "model_name": self.transcription.model_name,
                "segments_count": len(self.transcription.segments)
            }
        
        if self.translation:
            result["translation"] = self.translation.to_dict()
        
        return result


@dataclass
class ModelInfo:
    """模型信息数据类"""
    name: str
    size: str  # tiny, base, small, medium, large
    type: str  # multilingual, english
    file_size: Optional[int] = None  # 文件大小（字节）
    is_downloaded: bool = False
    download_url: Optional[str] = None
    
    @property
    def display_name(self) -> str:
        """显示名称"""
        if self.type == "english":
            return f"{self.size}.en"
        elif self.type == "turbo":
            return f"{self.size}-turbo"
        else:
            return self.size
    
    @property
    def file_size_mb(self) -> Optional[float]:
        """文件大小（MB）"""
        if self.file_size:
            return self.file_size / (1024 * 1024)
        return None


# 工具函数
def segments_to_dict_list(segments: List[Segment]) -> List[Dict[str, Any]]:
    """将Segment列表转换为字典列表（向后兼容）"""
    return [seg.to_dict() for seg in segments]


def dict_list_to_segments(dict_list: List[Dict[str, Any]]) -> List[Segment]:
    """将字典列表转换为Segment列表"""
    return [Segment.from_dict(d) for d in dict_list]


def merge_segments(segments: List[Segment], max_duration: float = 10.0, max_chars: int = 200) -> List[Segment]:
    """
    合并短字幕段
    
    Args:
        segments: 原始字幕段列表
        max_duration: 最大合并时长（秒）
        max_chars: 最大字符数
    
    Returns:
        合并后的字幕段列表
    """
    if not segments:
        return []
    
    merged = []
    current = segments[0]
    
    for next_seg in segments[1:]:
        # 检查是否可以合并
        combined_duration = next_seg.end - current.start
        combined_text = current.text + " " + next_seg.text
        
        if (combined_duration <= max_duration and 
            len(combined_text) <= max_chars and
            next_seg.start - current.end <= 2.0):  # 间隔不超过2秒
            
            # 合并
            current = Segment(
                start=current.start,
                end=next_seg.end,
                text=combined_text.strip(),
                language=current.language or next_seg.language
            )
        else:
            # 不能合并，保存当前段并开始新段
            merged.append(current)
            current = next_seg
    
    # 添加最后一段
    merged.append(current)
    return merged