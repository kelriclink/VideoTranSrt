"""
音频提取模块
使用 ffmpeg 从视频文件中提取音频
"""

import os
import tempfile
import subprocess
from pathlib import Path
from typing import Optional, Union
import ffmpeg


class AudioExtractor:
    """音频提取器"""
    
    def __init__(self):
        self.temp_dir = None
        # 创建程序目录下的 temp 文件夹
        self.program_temp_dir = Path(__file__).parent.parent / "temp"
        self.program_temp_dir.mkdir(exist_ok=True)
    
    def extract_audio(self, input_path: Union[str, Path], 
                     output_path: Optional[Union[str, Path]] = None) -> Path:
        """
        从视频文件中提取音频
        
        Args:
            input_path: 输入视频文件路径
            output_path: 输出音频文件路径，如果为None则使用临时文件
            
        Returns:
            提取的音频文件路径
        """
        input_path = Path(input_path)
        
        if not input_path.exists():
            raise FileNotFoundError(f"输入文件不存在: {input_path}")
        
        # 如果没有指定输出路径，创建临时文件
        if output_path is None:
            if self.temp_dir is None:
                # 使用程序目录下的 temp 文件夹而不是系统临时目录
                self.temp_dir = self.program_temp_dir
            output_path = Path(self.temp_dir) / f"{input_path.stem}.wav"
        else:
            output_path = Path(output_path)
        
        try:
            # 使用 ffmpeg 提取音频
            # 转换为 16kHz 单声道 WAV 格式，适合 Whisper
            (
                ffmpeg
                .input(str(input_path))
                .output(
                    str(output_path),
                    acodec='pcm_s16le',  # 16-bit PCM
                    ac=1,               # 单声道
                    ar=16000            # 16kHz 采样率
                )
                .overwrite_output()
                .run(quiet=True)
            )
            
            return output_path
            
        except ffmpeg.Error as e:
            raise RuntimeError(f"音频提取失败: {e.stderr.decode()}")
    
    def cleanup(self):
        """清理临时文件"""
        if self.temp_dir and os.path.exists(self.temp_dir):
            import shutil
            shutil.rmtree(self.temp_dir)
            self.temp_dir = None
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.cleanup()
