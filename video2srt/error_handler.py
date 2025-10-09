"""
错误处理和资源清理模块
提供统一的错误处理、资源管理和清理功能
"""

import os
import sys
import traceback
import tempfile
import shutil
import atexit
import signal
import threading
from typing import List, Dict, Any, Optional, Callable, Union
from pathlib import Path
from contextlib import contextmanager
from dataclasses import dataclass
from enum import Enum
import logging

from .reporter import Reporter


class ErrorLevel(Enum):
    """错误级别"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class ErrorCode(Enum):
    """错误代码"""
    # 文件相关错误
    FILE_NOT_FOUND = "FILE_NOT_FOUND"
    FILE_ACCESS_DENIED = "FILE_ACCESS_DENIED"
    FILE_CORRUPTED = "FILE_CORRUPTED"
    DISK_SPACE_INSUFFICIENT = "DISK_SPACE_INSUFFICIENT"
    
    # 网络相关错误
    NETWORK_TIMEOUT = "NETWORK_TIMEOUT"
    NETWORK_CONNECTION_FAILED = "NETWORK_CONNECTION_FAILED"
    API_RATE_LIMITED = "API_RATE_LIMITED"
    API_AUTHENTICATION_FAILED = "API_AUTHENTICATION_FAILED"
    
    # 模型相关错误
    MODEL_NOT_FOUND = "MODEL_NOT_FOUND"
    MODEL_LOAD_FAILED = "MODEL_LOAD_FAILED"
    MODEL_INCOMPATIBLE = "MODEL_INCOMPATIBLE"
    
    # 处理相关错误
    AUDIO_EXTRACTION_FAILED = "AUDIO_EXTRACTION_FAILED"
    TRANSCRIPTION_FAILED = "TRANSCRIPTION_FAILED"
    TRANSLATION_FAILED = "TRANSLATION_FAILED"
    FORMAT_CONVERSION_FAILED = "FORMAT_CONVERSION_FAILED"
    
    # 系统相关错误
    MEMORY_INSUFFICIENT = "MEMORY_INSUFFICIENT"
    CUDA_ERROR = "CUDA_ERROR"
    DEPENDENCY_MISSING = "DEPENDENCY_MISSING"
    
    # 配置相关错误
    CONFIG_INVALID = "CONFIG_INVALID"
    CONFIG_MISSING = "CONFIG_MISSING"
    
    # 未知错误
    UNKNOWN_ERROR = "UNKNOWN_ERROR"


@dataclass
class ErrorInfo:
    """错误信息"""
    code: ErrorCode
    level: ErrorLevel
    message: str
    details: Optional[str] = None
    traceback: Optional[str] = None
    timestamp: Optional[float] = None
    context: Optional[Dict[str, Any]] = None
    
    def __post_init__(self):
        if self.timestamp is None:
            import time
            self.timestamp = time.time()


class ResourceManager:
    """资源管理器"""
    
    def __init__(self, reporter: Optional[Reporter] = None):
        """
        初始化资源管理器
        
        Args:
            reporter: 日志报告器
        """
        self.reporter = reporter or Reporter()
        self.temp_files: List[Path] = []
        self.temp_dirs: List[Path] = []
        self.open_files: List[Any] = []
        self.processes: List[Any] = []
        self.cleanup_callbacks: List[Callable] = []
        self._lock = threading.Lock()
        self._signal_registered = False
        
        # 注册清理函数
        atexit.register(self.cleanup_all)
        
        # 只在主线程中注册信号处理器
        self._register_signal_handlers()
    
    def _register_signal_handlers(self):
        """注册信号处理器（仅在主线程中）"""
        try:
            # 检查是否在主线程中
            if threading.current_thread() is threading.main_thread() and not self._signal_registered:
                signal.signal(signal.SIGINT, self._signal_handler)
                signal.signal(signal.SIGTERM, self._signal_handler)
                self._signal_registered = True
                self.reporter.debug("信号处理器已注册")
            else:
                self.reporter.debug("跳过信号处理器注册（非主线程或已注册）")
        except Exception as e:
            self.reporter.warning(f"注册信号处理器失败: {e}")
    
    def _signal_handler(self, signum, frame):
        """信号处理器"""
        self.reporter.info(f"接收到信号 {signum}，开始清理资源...")
        self.cleanup_all()
        sys.exit(0)
    
    def register_temp_file(self, file_path: Union[str, Path]) -> Path:
        """
        注册临时文件
        
        Args:
            file_path: 文件路径
            
        Returns:
            文件路径对象
        """
        path = Path(file_path)
        with self._lock:
            if path not in self.temp_files:
                self.temp_files.append(path)
        return path
    
    def register_temp_dir(self, dir_path: Union[str, Path]) -> Path:
        """
        注册临时目录
        
        Args:
            dir_path: 目录路径
            
        Returns:
            目录路径对象
        """
        path = Path(dir_path)
        with self._lock:
            if path not in self.temp_dirs:
                self.temp_dirs.append(path)
        return path
    
    def register_file_handle(self, file_handle: Any):
        """
        注册文件句柄
        
        Args:
            file_handle: 文件句柄
        """
        with self._lock:
            if file_handle not in self.open_files:
                self.open_files.append(file_handle)
    
    def register_process(self, process: Any):
        """
        注册进程
        
        Args:
            process: 进程对象
        """
        with self._lock:
            if process not in self.processes:
                self.processes.append(process)
    
    def register_cleanup_callback(self, callback: Callable):
        """
        注册清理回调函数
        
        Args:
            callback: 清理回调函数
        """
        with self._lock:
            if callback not in self.cleanup_callbacks:
                self.cleanup_callbacks.append(callback)
    
    def create_temp_file(self, suffix: str = "", prefix: str = "video2srt_", 
                        dir: Optional[str] = None) -> Path:
        """
        创建临时文件
        
        Args:
            suffix: 文件后缀
            prefix: 文件前缀
            dir: 临时目录
            
        Returns:
            临时文件路径
        """
        fd, path = tempfile.mkstemp(suffix=suffix, prefix=prefix, dir=dir)
        os.close(fd)  # 关闭文件描述符
        temp_path = Path(path)
        self.register_temp_file(temp_path)
        return temp_path
    
    def create_temp_dir(self, prefix: str = "video2srt_", 
                       dir: Optional[str] = None) -> Path:
        """
        创建临时目录
        
        Args:
            prefix: 目录前缀
            dir: 父目录
            
        Returns:
            临时目录路径
        """
        path = tempfile.mkdtemp(prefix=prefix, dir=dir)
        temp_path = Path(path)
        self.register_temp_dir(temp_path)
        return temp_path
    
    def cleanup_temp_files(self):
        """清理临时文件"""
        with self._lock:
            for file_path in self.temp_files[:]:  # 创建副本以避免修改正在迭代的列表
                try:
                    if file_path.exists():
                        file_path.unlink()
                        self.reporter.debug(f"已删除临时文件: {file_path}")
                    self.temp_files.remove(file_path)
                except Exception as e:
                    self.reporter.warning(f"删除临时文件失败 {file_path}: {e}")
    
    def cleanup_temp_dirs(self):
        """清理临时目录"""
        with self._lock:
            for dir_path in self.temp_dirs[:]:  # 创建副本以避免修改正在迭代的列表
                try:
                    if dir_path.exists():
                        shutil.rmtree(dir_path)
                        self.reporter.debug(f"已删除临时目录: {dir_path}")
                    self.temp_dirs.remove(dir_path)
                except Exception as e:
                    self.reporter.warning(f"删除临时目录失败 {dir_path}: {e}")
    
    def cleanup_file_handles(self):
        """清理文件句柄"""
        with self._lock:
            for file_handle in self.open_files[:]:  # 创建副本
                try:
                    if hasattr(file_handle, 'close') and not file_handle.closed:
                        file_handle.close()
                        self.reporter.debug("已关闭文件句柄")
                    self.open_files.remove(file_handle)
                except Exception as e:
                    self.reporter.warning(f"关闭文件句柄失败: {e}")
    
    def cleanup_processes(self):
        """清理进程"""
        with self._lock:
            for process in self.processes[:]:  # 创建副本
                try:
                    if hasattr(process, 'terminate'):
                        process.terminate()
                        # 等待进程结束
                        if hasattr(process, 'wait'):
                            try:
                                process.wait(timeout=5)
                            except:
                                # 如果进程没有在5秒内结束，强制杀死
                                if hasattr(process, 'kill'):
                                    process.kill()
                        self.reporter.debug("已终止进程")
                    self.processes.remove(process)
                except Exception as e:
                    self.reporter.warning(f"终止进程失败: {e}")
    
    def cleanup_callbacks(self):
        """执行清理回调"""
        with self._lock:
            # 使用 __dict__ 访问属性避免方法名冲突
            callback_list = self.__dict__['cleanup_callbacks']
            callbacks_to_execute = list(callback_list)  # 创建副本
            for callback in callbacks_to_execute:
                try:
                    callback()
                except Exception as e:
                    self.reporter.warning(f"执行清理回调失败: {e}")
            # 清空回调列表
            callback_list.clear()
    
    def cleanup_all(self):
        """清理所有资源"""
        self.reporter.debug("开始清理所有资源...")
        
        # 按顺序清理资源
        # 直接调用清理回调的逻辑，避免方法名冲突
        with self._lock:
            callback_list = self.__dict__['cleanup_callbacks']
            callbacks_to_execute = list(callback_list)
            for callback in callbacks_to_execute:
                try:
                    callback()
                except Exception as e:
                    self.reporter.warning(f"执行清理回调失败: {e}")
            callback_list.clear()
        
        self.cleanup_processes()
        self.cleanup_file_handles()
        self.cleanup_temp_files()
        self.cleanup_temp_dirs()
        
        self.reporter.debug("资源清理完成")


class ErrorHandler:
    """错误处理器"""
    
    def __init__(self, reporter: Optional[Reporter] = None):
        """
        初始化错误处理器
        
        Args:
            reporter: 日志报告器
        """
        self.reporter = reporter or Reporter()
        self.error_history: List[ErrorInfo] = []
        self.error_callbacks: Dict[ErrorCode, List[Callable]] = {}
        self.resource_manager = ResourceManager(reporter)
    
    def register_error_callback(self, error_code: ErrorCode, callback: Callable):
        """
        注册错误回调函数
        
        Args:
            error_code: 错误代码
            callback: 回调函数
        """
        if error_code not in self.error_callbacks:
            self.error_callbacks[error_code] = []
        self.error_callbacks[error_code].append(callback)
    
    def handle_error(self, error: Union[Exception, ErrorInfo], 
                    context: Optional[Dict[str, Any]] = None) -> ErrorInfo:
        """
        处理错误
        
        Args:
            error: 错误对象或错误信息
            context: 错误上下文
            
        Returns:
            错误信息对象
        """
        if isinstance(error, ErrorInfo):
            error_info = error
        else:
            error_info = self._create_error_info(error, context)
        
        # 记录错误
        self.error_history.append(error_info)
        
        # 记录日志
        self._log_error(error_info)
        
        # 执行错误回调
        self._execute_error_callbacks(error_info)
        
        return error_info
    
    def _create_error_info(self, error: Exception, 
                          context: Optional[Dict[str, Any]] = None) -> ErrorInfo:
        """
        创建错误信息对象
        
        Args:
            error: 异常对象
            context: 错误上下文
            
        Returns:
            错误信息对象
        """
        # 根据异常类型确定错误代码和级别
        error_code, error_level = self._classify_error(error)
        
        return ErrorInfo(
            code=error_code,
            level=error_level,
            message=str(error),
            details=self._get_error_details(error),
            traceback=traceback.format_exc(),
            context=context
        )
    
    def _classify_error(self, error: Exception) -> tuple[ErrorCode, ErrorLevel]:
        """
        分类错误
        
        Args:
            error: 异常对象
            
        Returns:
            错误代码和错误级别的元组
        """
        error_type = type(error).__name__
        error_message = str(error).lower()
        
        # 文件相关错误
        if isinstance(error, FileNotFoundError):
            return ErrorCode.FILE_NOT_FOUND, ErrorLevel.ERROR
        elif isinstance(error, PermissionError):
            return ErrorCode.FILE_ACCESS_DENIED, ErrorLevel.ERROR
        elif "no space left" in error_message or "disk full" in error_message:
            return ErrorCode.DISK_SPACE_INSUFFICIENT, ErrorLevel.CRITICAL
        
        # 网络相关错误
        elif "timeout" in error_message:
            return ErrorCode.NETWORK_TIMEOUT, ErrorLevel.WARNING
        elif "connection" in error_message and "failed" in error_message:
            return ErrorCode.NETWORK_CONNECTION_FAILED, ErrorLevel.WARNING
        elif "rate limit" in error_message or "too many requests" in error_message:
            return ErrorCode.API_RATE_LIMITED, ErrorLevel.WARNING
        elif "authentication" in error_message or "unauthorized" in error_message:
            return ErrorCode.API_AUTHENTICATION_FAILED, ErrorLevel.ERROR
        
        # 内存相关错误
        elif isinstance(error, MemoryError) or "out of memory" in error_message:
            return ErrorCode.MEMORY_INSUFFICIENT, ErrorLevel.CRITICAL
        
        # CUDA相关错误
        elif "cuda" in error_message.lower():
            return ErrorCode.CUDA_ERROR, ErrorLevel.ERROR
        
        # 模型相关错误
        elif "model" in error_message and "not found" in error_message:
            return ErrorCode.MODEL_NOT_FOUND, ErrorLevel.ERROR
        elif "model" in error_message and ("load" in error_message or "loading" in error_message):
            return ErrorCode.MODEL_LOAD_FAILED, ErrorLevel.ERROR
        
        # 默认为未知错误
        else:
            return ErrorCode.UNKNOWN_ERROR, ErrorLevel.ERROR
    
    def _get_error_details(self, error: Exception) -> Optional[str]:
        """
        获取错误详细信息
        
        Args:
            error: 异常对象
            
        Returns:
            错误详细信息
        """
        details = []
        
        # 添加异常类型
        details.append(f"异常类型: {type(error).__name__}")
        
        # 添加异常参数
        if hasattr(error, 'args') and error.args:
            details.append(f"异常参数: {error.args}")
        
        # 添加特定属性
        if hasattr(error, 'errno'):
            details.append(f"错误代码: {error.errno}")
        if hasattr(error, 'filename'):
            details.append(f"文件名: {error.filename}")
        
        return "; ".join(details) if details else None
    
    def _log_error(self, error_info: ErrorInfo):
        """
        记录错误日志
        
        Args:
            error_info: 错误信息
        """
        message = f"[{error_info.code.value}] {error_info.message}"
        
        if error_info.details:
            message += f" - {error_info.details}"
        
        if error_info.level == ErrorLevel.CRITICAL:
            self.reporter.error(message)
        elif error_info.level == ErrorLevel.ERROR:
            self.reporter.error(message)
        elif error_info.level == ErrorLevel.WARNING:
            self.reporter.warning(message)
        else:
            self.reporter.info(message)
        
        # 记录堆栈跟踪（仅在调试模式下）
        if error_info.traceback and self.reporter.logger.level <= logging.DEBUG:
            self.reporter.debug(f"堆栈跟踪:\n{error_info.traceback}")
    
    def _execute_error_callbacks(self, error_info: ErrorInfo):
        """
        执行错误回调函数
        
        Args:
            error_info: 错误信息
        """
        callbacks = self.error_callbacks.get(error_info.code, [])
        for callback in callbacks:
            try:
                callback(error_info)
            except Exception as e:
                self.reporter.warning(f"执行错误回调失败: {e}")
    
    def get_error_summary(self) -> Dict[str, Any]:
        """
        获取错误摘要
        
        Returns:
            错误摘要字典
        """
        if not self.error_history:
            return {"total_errors": 0, "error_counts": {}, "recent_errors": []}
        
        # 统计错误数量
        error_counts = {}
        for error_info in self.error_history:
            code = error_info.code.value
            error_counts[code] = error_counts.get(code, 0) + 1
        
        # 获取最近的错误
        recent_errors = []
        for error_info in self.error_history[-10:]:  # 最近10个错误
            recent_errors.append({
                "code": error_info.code.value,
                "level": error_info.level.value,
                "message": error_info.message,
                "timestamp": error_info.timestamp
            })
        
        return {
            "total_errors": len(self.error_history),
            "error_counts": error_counts,
            "recent_errors": recent_errors
        }
    
    @contextmanager
    def error_context(self, context: Dict[str, Any]):
        """
        错误上下文管理器
        
        Args:
            context: 上下文信息
        """
        try:
            yield
        except Exception as e:
            self.handle_error(e, context)
            raise


# 全局错误处理器实例
error_handler = ErrorHandler()
resource_manager = error_handler.resource_manager