"""
Video2SRT - 视频/音频转字幕生成器
主模块入口
"""

__version__ = "1.0.0"
__author__ = "Your Name"
__email__ = "your.email@example.com"

from .core import Video2SRT
from .cli import main

__all__ = ["Video2SRT", "main"]
