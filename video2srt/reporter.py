"""
统一的日志和通知系统
管理CLI/GUI的输出、等级和回调
"""

import logging
import sys
from enum import Enum
from pathlib import Path
from typing import Optional, Callable, Any
from datetime import datetime


class LogLevel(Enum):
    """日志级别"""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"


class Reporter:
    """统一的报告器，处理日志、状态通知和进度更新"""
    
    def __init__(self, 
                 log_file: Optional[str] = None,
                 console_output: bool = True,
                 status_callback: Optional[Callable[[str], None]] = None,
                 progress_callback: Optional[Callable[[int], None]] = None,
                 log_callback: Optional[Callable[[str], None]] = None):
        """
        初始化报告器
        
        Args:
            log_file: 日志文件路径
            console_output: 是否输出到控制台
            status_callback: 状态更新回调
            progress_callback: 进度更新回调
            log_callback: 日志回调
        """
        self.console_output = console_output
        self.status_callback = status_callback
        self.progress_callback = progress_callback
        self.log_callback = log_callback
        
        # 设置日志
        self.logger = logging.getLogger('video2srt')
        self.logger.setLevel(logging.DEBUG)
        
        # 清除现有处理器
        self.logger.handlers.clear()
        
        # 控制台处理器
        if console_output:
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setLevel(logging.INFO)
            console_formatter = logging.Formatter(
                '%(asctime)s - %(levelname)s - %(message)s',
                datefmt='%H:%M:%S'
            )
            console_handler.setFormatter(console_formatter)
            self.logger.addHandler(console_handler)
        
        # 文件处理器
        if log_file:
            log_path = Path(log_file)
            log_path.parent.mkdir(parents=True, exist_ok=True)
            
            file_handler = logging.FileHandler(log_file, encoding='utf-8')
            file_handler.setLevel(logging.DEBUG)
            file_formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            file_handler.setFormatter(file_formatter)
            self.logger.addHandler(file_handler)
    
    def debug(self, message: str):
        """调试信息"""
        self.logger.debug(message)
        self._notify_log(message, LogLevel.DEBUG)
    
    def info(self, message: str):
        """一般信息"""
        self.logger.info(message)
        self._notify_log(message, LogLevel.INFO)
    
    def warning(self, message: str):
        """警告信息"""
        self.logger.warning(message)
        self._notify_log(message, LogLevel.WARNING)
    
    def error(self, message: str):
        """错误信息"""
        self.logger.error(message)
        self._notify_log(message, LogLevel.ERROR)
    
    def status(self, message: str):
        """状态更新"""
        self.info(message)
        if self.status_callback:
            try:
                self.status_callback(message)
            except Exception as e:
                self.logger.error(f"状态回调失败: {e}")
    
    def progress(self, value: int, message: str = ""):
        """进度更新"""
        # 确保进度值在有效范围内
        value = max(0, min(100, int(value)))
        
        if message:
            self.debug(f"进度: {value}% - {message}")
        else:
            self.debug(f"进度: {value}%")
        
        if self.progress_callback:
            try:
                self.progress_callback(value)
            except Exception as e:
                self.logger.error(f"进度回调失败: {e}")
    
    def step(self, step_name: str, current: int, total: int):
        """步骤进度"""
        percentage = int((current / total) * 100) if total > 0 else 0
        message = f"步骤 {current}/{total}: {step_name}"
        self.status(message)
        self.progress(percentage, step_name)
    
    def _notify_log(self, message: str, level: LogLevel):
        """通知日志回调"""
        if self.log_callback:
            try:
                formatted_message = f"[{level.value}] {message}"
                self.log_callback(formatted_message)
            except Exception as e:
                self.logger.error(f"日志回调失败: {e}")
    
    def exception(self, message: str, exc: Exception):
        """异常信息"""
        full_message = f"{message}: {str(exc)}"
        self.logger.exception(full_message)
        self._notify_log(full_message, LogLevel.ERROR)
    
    def section(self, title: str):
        """章节标题"""
        separator = "=" * 50
        self.info(f"\n{separator}")
        self.info(f"{title}")
        self.info(separator)


def create_reporter(log_file: Optional[str] = None, **kwargs) -> Reporter:
    """
    创建报告器实例
    
    Args:
        log_file: 日志文件路径，None表示不写文件
        **kwargs: 其他Reporter参数
    
    Returns:
        Reporter实例
    """
    # 默认日志文件路径
    if log_file is None:
        log_dir = Path("logs")
        log_dir.mkdir(exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_file = log_dir / f"video2srt_{timestamp}.log"
    
    return Reporter(log_file=str(log_file), **kwargs)


def create_console_reporter(**kwargs) -> Reporter:
    """创建仅控制台输出的报告器"""
    return Reporter(log_file=None, console_output=True, **kwargs)


def create_gui_reporter(status_callback=None, progress_callback=None, log_callback=None) -> Reporter:
    """创建GUI专用的报告器"""
    return create_reporter(
        console_output=False,
        status_callback=status_callback,
        progress_callback=progress_callback,
        log_callback=log_callback
    )