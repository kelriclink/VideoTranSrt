"""
输出格式支持模块
支持多种字幕格式：SRT, WebVTT, ASS
"""

import re
from pathlib import Path
from typing import List, Dict, Any, Union, Optional
from dataclasses import dataclass
from abc import ABC, abstractmethod

from .models import Segment


@dataclass
class FormatConfig:
    """格式配置"""
    name: str
    extension: str
    mime_type: str
    supports_styling: bool = False
    supports_positioning: bool = False
    supports_metadata: bool = False


class BaseFormatter(ABC):
    """基础格式化器抽象类"""
    
    @abstractmethod
    def format_segments(self, segments: List[Segment], **kwargs) -> str:
        """
        格式化字幕段落
        
        Args:
            segments: 字幕段落列表
            **kwargs: 额外参数
            
        Returns:
            格式化后的字幕内容
        """
        pass
    
    @abstractmethod
    def get_config(self) -> FormatConfig:
        """
        获取格式配置
        
        Returns:
            格式配置对象
        """
        pass
    
    def save_to_file(self, content: str, file_path: Union[str, Path]):
        """
        保存内容到文件
        
        Args:
            content: 字幕内容
            file_path: 文件路径
        """
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)


class SRTFormatter(BaseFormatter):
    """SRT格式化器"""
    
    @staticmethod
    def format_time(seconds: float) -> str:
        """
        格式化时间为SRT格式
        
        Args:
            seconds: 秒数
            
        Returns:
            SRT时间格式字符串
        """
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        millisecs = int((seconds % 1) * 1000)
        return f"{hours:02d}:{minutes:02d}:{secs:02d},{millisecs:03d}"
    
    def format_segment(self, segment: Union[Segment, Dict], index: int) -> str:
        """
        格式化单个字幕段落
        
        Args:
            segment: 字幕段落
            index: 段落索引
            
        Returns:
            格式化后的段落字符串
        """
        if isinstance(segment, Segment):
            start_time = self.format_time(segment.start)
            end_time = self.format_time(segment.end)
            text = segment.text
        else:
            start_time = self.format_time(segment['start'])
            end_time = self.format_time(segment['end'])
            text = segment['text']
        
        return f"{index}\n{start_time} --> {end_time}\n{text}\n"
    
    def format_segments(self, segments: List[Union[Segment, Dict]], **kwargs) -> str:
        """
        格式化字幕段落列表
        
        Args:
            segments: 字幕段落列表
            **kwargs: 额外参数
            
        Returns:
            完整的SRT内容
        """
        srt_content = []
        for i, segment in enumerate(segments, 1):
            srt_content.append(self.format_segment(segment, i))
        
        return "\n".join(srt_content)
    
    def create_bilingual_srt(self, original_segments: List[Union[Segment, Dict]], 
                           translated_segments: List[Union[Segment, Dict]]) -> str:
        """
        创建双语SRT内容
        
        Args:
            original_segments: 原文段落列表
            translated_segments: 译文段落列表
            
        Returns:
            双语SRT内容
        """
        srt_content = []
        
        for i, (orig, trans) in enumerate(zip(original_segments, translated_segments), 1):
            # 提取时间和文本
            if isinstance(orig, Segment):
                start_time = self.format_time(orig.start)
                end_time = self.format_time(orig.end)
                orig_text = orig.text
            else:
                start_time = self.format_time(orig['start'])
                end_time = self.format_time(orig['end'])
                orig_text = orig['text']
            
            if isinstance(trans, Segment):
                trans_text = trans.text
            else:
                trans_text = trans['text']
            
            # 组合双语文本
            bilingual_text = f"{orig_text}\n{trans_text}"
            
            srt_content.append(f"{i}\n{start_time} --> {end_time}\n{bilingual_text}\n")
        
        return "\n".join(srt_content)
    
    def get_config(self) -> FormatConfig:
        """获取SRT格式配置"""
        return FormatConfig(
            name="SubRip",
            extension=".srt",
            mime_type="application/x-subrip",
            supports_styling=False,
            supports_positioning=False,
            supports_metadata=False
        )


class WebVTTFormatter(BaseFormatter):
    """WebVTT格式化器"""
    
    @staticmethod
    def format_time(seconds: float) -> str:
        """
        格式化时间为WebVTT格式
        
        Args:
            seconds: 秒数
            
        Returns:
            WebVTT时间格式字符串
        """
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = seconds % 60
        
        if hours > 0:
            return f"{hours:02d}:{minutes:02d}:{secs:06.3f}"
        else:
            return f"{minutes:02d}:{secs:06.3f}"
    
    def format_segment(self, segment: Union[Segment, Dict], cue_id: Optional[str] = None) -> str:
        """
        格式化单个字幕段落
        
        Args:
            segment: 字幕段落
            cue_id: 可选的cue标识符
            
        Returns:
            格式化后的段落字符串
        """
        if isinstance(segment, Segment):
            start_time = self.format_time(segment.start)
            end_time = self.format_time(segment.end)
            text = segment.text
        else:
            start_time = self.format_time(segment['start'])
            end_time = self.format_time(segment['end'])
            text = segment['text']
        
        cue_content = []
        if cue_id:
            cue_content.append(cue_id)
        cue_content.append(f"{start_time} --> {end_time}")
        cue_content.append(text)
        cue_content.append("")  # 空行分隔
        
        return "\n".join(cue_content)
    
    def format_segments(self, segments: List[Union[Segment, Dict]], 
                       title: Optional[str] = None, **kwargs) -> str:
        """
        格式化字幕段落列表
        
        Args:
            segments: 字幕段落列表
            title: 可选的标题
            **kwargs: 额外参数
            
        Returns:
            完整的WebVTT内容
        """
        vtt_content = ["WEBVTT"]
        
        if title:
            vtt_content.append(f"Title: {title}")
        
        vtt_content.append("")  # 空行
        
        for i, segment in enumerate(segments):
            cue_id = f"cue-{i+1}"
            vtt_content.append(self.format_segment(segment, cue_id))
        
        return "\n".join(vtt_content)
    
    def create_bilingual_vtt(self, original_segments: List[Union[Segment, Dict]], 
                           translated_segments: List[Union[Segment, Dict]],
                           title: Optional[str] = None) -> str:
        """
        创建双语WebVTT内容
        
        Args:
            original_segments: 原文段落列表
            translated_segments: 译文段落列表
            title: 可选的标题
            
        Returns:
            双语WebVTT内容
        """
        vtt_content = ["WEBVTT"]
        
        if title:
            vtt_content.append(f"Title: {title}")
        
        vtt_content.append("")  # 空行
        
        for i, (orig, trans) in enumerate(zip(original_segments, translated_segments)):
            # 提取时间和文本
            if isinstance(orig, Segment):
                start_time = self.format_time(orig.start)
                end_time = self.format_time(orig.end)
                orig_text = orig.text
            else:
                start_time = self.format_time(orig['start'])
                end_time = self.format_time(orig['end'])
                orig_text = orig['text']
            
            if isinstance(trans, Segment):
                trans_text = trans.text
            else:
                trans_text = trans['text']
            
            # 组合双语文本
            bilingual_text = f"{orig_text}\n{trans_text}"
            
            cue_id = f"cue-{i+1}"
            vtt_content.append(f"{cue_id}\n{start_time} --> {end_time}\n{bilingual_text}\n")
        
        return "\n".join(vtt_content)
    
    def get_config(self) -> FormatConfig:
        """获取WebVTT格式配置"""
        return FormatConfig(
            name="WebVTT",
            extension=".vtt",
            mime_type="text/vtt",
            supports_styling=True,
            supports_positioning=True,
            supports_metadata=True
        )


class ASSFormatter(BaseFormatter):
    """ASS (Advanced SubStation Alpha) 格式化器"""
    
    def __init__(self):
        """初始化ASS格式化器"""
        self.default_style = {
            'Name': 'Default',
            'Fontname': 'Arial',
            'Fontsize': '20',
            'PrimaryColour': '&Hffffff',
            'SecondaryColour': '&Hffffff',
            'OutlineColour': '&H0',
            'BackColour': '&H80000000',
            'Bold': '0',
            'Italic': '0',
            'Underline': '0',
            'StrikeOut': '0',
            'ScaleX': '100',
            'ScaleY': '100',
            'Spacing': '0',
            'Angle': '0',
            'BorderStyle': '1',
            'Outline': '2',
            'Shadow': '0',
            'Alignment': '2',
            'MarginL': '10',
            'MarginR': '10',
            'MarginV': '10',
            'Encoding': '1'
        }
    
    @staticmethod
    def format_time(seconds: float) -> str:
        """
        格式化时间为ASS格式
        
        Args:
            seconds: 秒数
            
        Returns:
            ASS时间格式字符串
        """
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = seconds % 60
        return f"{hours}:{minutes:02d}:{secs:05.2f}"
    
    def get_header(self, title: Optional[str] = None) -> str:
        """
        获取ASS文件头部
        
        Args:
            title: 可选的标题
            
        Returns:
            ASS文件头部内容
        """
        header = [
            "[Script Info]",
            f"Title: {title or 'Video2SRT Generated Subtitles'}",
            "ScriptType: v4.00+",
            "WrapStyle: 0",
            "ScaledBorderAndShadow: yes",
            "YCbCr Matrix: TV.601",
            "",
            "[V4+ Styles]",
            "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding"
        ]
        
        # 添加默认样式
        style_line = "Style: " + ",".join(self.default_style.values())
        header.append(style_line)
        
        header.extend([
            "",
            "[Events]",
            "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text"
        ])
        
        return "\n".join(header)
    
    def format_segment(self, segment: Union[Segment, Dict], style: str = "Default") -> str:
        """
        格式化单个字幕段落
        
        Args:
            segment: 字幕段落
            style: 样式名称
            
        Returns:
            格式化后的段落字符串
        """
        if isinstance(segment, Segment):
            start_time = self.format_time(segment.start)
            end_time = self.format_time(segment.end)
            text = segment.text
        else:
            start_time = self.format_time(segment['start'])
            end_time = self.format_time(segment['end'])
            text = segment['text']
        
        # 转义ASS特殊字符
        text = text.replace('\\', '\\\\').replace('{', '\\{').replace('}', '\\}')
        
        return f"Dialogue: 0,{start_time},{end_time},{style},,0,0,0,,{text}"
    
    def format_segments(self, segments: List[Union[Segment, Dict]], 
                       title: Optional[str] = None, **kwargs) -> str:
        """
        格式化字幕段落列表
        
        Args:
            segments: 字幕段落列表
            title: 可选的标题
            **kwargs: 额外参数
            
        Returns:
            完整的ASS内容
        """
        ass_content = [self.get_header(title)]
        
        for segment in segments:
            ass_content.append(self.format_segment(segment))
        
        return "\n".join(ass_content)
    
    def create_bilingual_ass(self, original_segments: List[Union[Segment, Dict]], 
                           translated_segments: List[Union[Segment, Dict]],
                           title: Optional[str] = None) -> str:
        """
        创建双语ASS内容
        
        Args:
            original_segments: 原文段落列表
            translated_segments: 译文段落列表
            title: 可选的标题
            
        Returns:
            双语ASS内容
        """
        # 创建双语样式
        bilingual_style = self.default_style.copy()
        bilingual_style['Name'] = 'Bilingual'
        bilingual_style['Fontsize'] = '18'  # 稍小的字体
        
        header = [
            "[Script Info]",
            f"Title: {title or 'Video2SRT Generated Bilingual Subtitles'}",
            "ScriptType: v4.00+",
            "WrapStyle: 0",
            "ScaledBorderAndShadow: yes",
            "YCbCr Matrix: TV.601",
            "",
            "[V4+ Styles]",
            "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding"
        ]
        
        # 添加默认样式和双语样式
        default_style_line = "Style: " + ",".join(self.default_style.values())
        bilingual_style_line = "Style: " + ",".join(bilingual_style.values())
        header.extend([default_style_line, bilingual_style_line])
        
        header.extend([
            "",
            "[Events]",
            "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text"
        ])
        
        ass_content = ["\n".join(header)]
        
        for orig, trans in zip(original_segments, translated_segments):
            # 提取时间和文本
            if isinstance(orig, Segment):
                start_time = self.format_time(orig.start)
                end_time = self.format_time(orig.end)
                orig_text = orig.text
            else:
                start_time = self.format_time(orig['start'])
                end_time = self.format_time(orig['end'])
                orig_text = orig['text']
            
            if isinstance(trans, Segment):
                trans_text = trans.text
            else:
                trans_text = trans['text']
            
            # 转义特殊字符
            orig_text = orig_text.replace('\\', '\\\\').replace('{', '\\{').replace('}', '\\}')
            trans_text = trans_text.replace('\\', '\\\\').replace('{', '\\{').replace('}', '\\}')
            
            # 组合双语文本，使用换行符分隔
            bilingual_text = f"{orig_text}\\N{trans_text}"
            
            ass_content.append(f"Dialogue: 0,{start_time},{end_time},Bilingual,,0,0,0,,{bilingual_text}")
        
        return "\n".join(ass_content)
    
    def get_config(self) -> FormatConfig:
        """获取ASS格式配置"""
        return FormatConfig(
            name="Advanced SubStation Alpha",
            extension=".ass",
            mime_type="text/x-ass",
            supports_styling=True,
            supports_positioning=True,
            supports_metadata=True
        )


class OutputFormatManager:
    """输出格式管理器"""
    
    def __init__(self):
        """初始化格式管理器"""
        self.formatters = {
            'srt': SRTFormatter(),
            'vtt': WebVTTFormatter(),
            'ass': ASSFormatter()
        }
    
    def get_formatter(self, format_name: str) -> BaseFormatter:
        """
        获取格式化器
        
        Args:
            format_name: 格式名称
            
        Returns:
            格式化器实例
            
        Raises:
            ValueError: 不支持的格式
        """
        formatter = self.formatters.get(format_name.lower())
        if not formatter:
            raise ValueError(f"不支持的格式: {format_name}")
        return formatter
    
    def get_supported_formats(self) -> List[str]:
        """
        获取支持的格式列表
        
        Returns:
            支持的格式名称列表
        """
        return list(self.formatters.keys())
    
    def get_format_info(self, format_name: str) -> FormatConfig:
        """
        获取格式信息
        
        Args:
            format_name: 格式名称
            
        Returns:
            格式配置对象
        """
        formatter = self.get_formatter(format_name)
        return formatter.get_config()
    
    def detect_format_from_extension(self, file_path: Union[str, Path]) -> Optional[str]:
        """
        从文件扩展名检测格式
        
        Args:
            file_path: 文件路径
            
        Returns:
            格式名称，如果无法检测则返回None
        """
        path = Path(file_path)
        extension = path.suffix.lower()
        
        for format_name, formatter in self.formatters.items():
            if formatter.get_config().extension == extension:
                return format_name
        
        return None
    
    def convert_segments(self, segments: List[Union[Segment, Dict]], 
                        output_format: str, output_path: Union[str, Path],
                        **kwargs) -> Path:
        """
        转换字幕段落到指定格式
        
        Args:
            segments: 字幕段落列表
            output_format: 输出格式
            output_path: 输出路径
            **kwargs: 额外参数
            
        Returns:
            输出文件路径
        """
        formatter = self.get_formatter(output_format)
        content = formatter.format_segments(segments, **kwargs)
        
        output_path = Path(output_path)
        formatter.save_to_file(content, output_path)
        
        return output_path
    
    def convert_bilingual_segments(self, original_segments: List[Union[Segment, Dict]], 
                                 translated_segments: List[Union[Segment, Dict]],
                                 output_format: str, output_path: Union[str, Path],
                                 **kwargs) -> Path:
        """
        转换双语字幕段落到指定格式
        
        Args:
            original_segments: 原文段落列表
            translated_segments: 译文段落列表
            output_format: 输出格式
            output_path: 输出路径
            **kwargs: 额外参数
            
        Returns:
            输出文件路径
        """
        formatter = self.get_formatter(output_format)
        
        if output_format == 'srt':
            content = formatter.create_bilingual_srt(original_segments, translated_segments)
        elif output_format == 'vtt':
            content = formatter.create_bilingual_vtt(original_segments, translated_segments, **kwargs)
        elif output_format == 'ass':
            content = formatter.create_bilingual_ass(original_segments, translated_segments, **kwargs)
        else:
            raise ValueError(f"格式 {output_format} 不支持双语输出")
        
        output_path = Path(output_path)
        formatter.save_to_file(content, output_path)
        
        return output_path


# 全局格式管理器实例
output_format_manager = OutputFormatManager()