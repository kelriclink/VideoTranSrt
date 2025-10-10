"""
SRT 格式化模块
将转录结果转换为标准 SRT 字幕格式
"""

from typing import List, Dict, Any, Union
from pathlib import Path
from .models import Segment


class SRTFormatter:
    """SRT 格式化器"""
    
    @staticmethod
    def format_time(seconds: float) -> str:
        """
        将秒数转换为 SRT 时间格式 (HH:MM:SS,mmm)
        
        Args:
            seconds: 秒数
            
        Returns:
            SRT 时间格式字符串
        """
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        # 修复毫秒精度问题，使用四舍五入
        millisecs = round((seconds % 1) * 1000)
        
        return f"{hours:02d}:{minutes:02d}:{secs:02d},{millisecs:03d}"
    
    @staticmethod
    def format_segment(segment: Union[Segment, Dict[str, Any]], index: int) -> str:
        """
        格式化单个字幕段
        
        Args:
            segment: 字幕段数据（Segment对象或字典）
            index: 字幕段序号
            
        Returns:
            格式化的字幕段字符串
        """
        if isinstance(segment, Segment):
            start_time = SRTFormatter.format_time(segment.start)
            end_time = SRTFormatter.format_time(segment.end)
            text = segment.text.strip()
        else:
            start_time = SRTFormatter.format_time(segment["start"])
            end_time = SRTFormatter.format_time(segment["end"])
            text = segment["text"].strip()
        
        return f"{index}\n{start_time} --> {end_time}\n{text}\n"
    
    @staticmethod
    def format_segments(segments: List[Union[Segment, Dict[str, Any]]], min_duration: float = 0.5) -> str:
        """
        格式化所有字幕段
        
        Args:
            segments: 字幕段列表（Segment对象或字典）
            
        Returns:
            完整的 SRT 格式字符串
        """
        # 先进行时间合法性修正，避免零时长/时间倒退导致播放器无法加载
        # 归一化为字典，便于处理
        norm_segments: List[Dict[str, Any]] = []
        for seg in segments:
            if isinstance(seg, Segment):
                start = float(getattr(seg, 'start', 0.0) or 0.0)
                end = float(getattr(seg, 'end', start) if getattr(seg, 'end', None) is not None else start)
                text = (getattr(seg, 'text', '') or '').strip()
            else:
                start = float(seg.get('start', 0.0) or 0.0)
                end = float(seg.get('end', start) if seg.get('end', None) is not None else start)
                text = (seg.get('text', '') or '').strip()
            if not text:
                continue
            if start < 0:
                start = 0.0
            if end < 0:
                end = 0.0
            norm_segments.append({"start": start, "end": end, "text": text})

        # 排序并修正时间
        norm_segments.sort(key=lambda s: (s["start"], s["end"]))
        fixed: List[Dict[str, Any]] = []
        last_end = 0.0
        for seg in norm_segments:
            start = seg["start"]
            end = seg["end"]
            text = seg["text"]
            if start < last_end:
                start = last_end
            if end <= start:
                end = start + min_duration
            if (end - start) < min_duration:
                end = start + min_duration
            fixed.append({"start": start, "end": end, "text": text})
            last_end = end

        # 输出
        srt_content = []
        for i, segment in enumerate(fixed, 1):
            srt_content.append(SRTFormatter.format_segment(segment, i))
        return "\n".join(srt_content)
    
    @staticmethod
    def save_srt(content: str, output_path: Path) -> None:
        """
        保存 SRT 内容到文件
        
        Args:
            content: SRT 格式内容
            output_path: 输出文件路径
        """
        output_path = Path(output_path)
        
        # 确保输出目录存在
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # 保存文件，使用 UTF-8 编码
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(content)
    
    @staticmethod
    def create_bilingual_srt(original_segments: List[Union[Segment, Dict[str, Any]]], 
                           translated_segments: List[Union[Segment, Dict[str, Any]]]) -> str:
        """
        创建双语字幕
        
        Args:
            original_segments: 原始字幕段（Segment对象或字典）
            translated_segments: 翻译字幕段（Segment对象或字典）
            
        Returns:
            双语 SRT 格式字符串
        """
        srt_content = []
        
        for i, (orig, trans) in enumerate(zip(original_segments, translated_segments), 1):
            # 处理Segment对象或字典
            if isinstance(orig, Segment):
                start_time = SRTFormatter.format_time(orig.start)
                end_time = SRTFormatter.format_time(orig.end)
                orig_text = orig.text.strip()
            else:
                start_time = SRTFormatter.format_time(orig["start"])
                end_time = SRTFormatter.format_time(orig["end"])
                orig_text = orig["text"].strip()
            
            if isinstance(trans, Segment):
                trans_text = trans.text.strip()
            else:
                trans_text = trans["text"].strip()
            
            # 双语字幕：原文 + 翻译
            text = f"{orig_text}\n{trans_text}"
            
            srt_content.append(f"{i}\n{start_time} --> {end_time}\n{text}\n")
        
        return "\n".join(srt_content)
    
    @staticmethod
    def merge_short_segments(segments: List[Dict[str, Any]], 
                           min_duration: float = 1.0) -> List[Dict[str, Any]]:
        """
        合并过短的字幕段
        
        Args:
            segments: 字幕段列表
            min_duration: 最小持续时间（秒）
            
        Returns:
            合并后的字幕段列表
        """
        if not segments:
            return segments
        
        merged = []
        current_segment = segments[0].copy()
        
        for segment in segments[1:]:
            # 如果当前段太短，尝试与下一段合并
            if (current_segment["end"] - current_segment["start"]) < min_duration:
                # 合并文本
                current_segment["text"] += " " + segment["text"]
                current_segment["end"] = segment["end"]
            else:
                # 当前段足够长，添加到结果中
                merged.append(current_segment)
                current_segment = segment.copy()
        
        # 添加最后一个段
        merged.append(current_segment)
        
        return merged
