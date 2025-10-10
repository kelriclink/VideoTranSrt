"""
模型加载器插件基类
定义插件接口和通用功能
"""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional, Dict, Any, List, Callable


class BaseModelLoaderPlugin(ABC):
    """模型加载器插件基类"""
    
    def __init__(self, model_size: str, model_path: Optional[str] = None, **kwargs):
        """
        初始化插件
        
        Args:
            model_size: 模型大小/名称
            model_path: 模型路径
            **kwargs: 其他参数
        """
        self.model_size = model_size
        self.model_path = Path(model_path) if model_path else self._get_default_model_path()
        self.config = kwargs
        self._model = None
    
    def _get_default_model_path(self) -> Path:
        """获取默认模型路径"""
        project_root = Path(__file__).parent.parent.parent
        return project_root / "model"
    
    @property
    @abstractmethod
    def plugin_name(self) -> str:
        """插件名称"""
        pass
    
    @property
    @abstractmethod
    def plugin_version(self) -> str:
        """插件版本"""
        pass
    
    @property
    @abstractmethod
    def supported_models(self) -> List[str]:
        """支持的模型列表或模式"""
        pass
    
    @abstractmethod
    def is_supported(self, model_size: str) -> bool:
        """
        检查是否支持指定的模型
        
        Args:
            model_size: 模型大小/名称
            
        Returns:
            是否支持该模型
        """
        pass
    
    @abstractmethod
    def load(self):
        """
        加载模型
        
        Returns:
            加载的模型对象
        """
        pass
    
    def unload(self):
        """卸载模型，释放资源"""
        if self._model is not None:
            del self._model
            self._model = None
    
    def get_plugin_info(self) -> Dict[str, Any]:
        """获取插件信息"""
        return {
            "name": self.plugin_name,
            "version": self.plugin_version,
            "supported_models": self.supported_models,
            "model_size": self.model_size,
            "model_path": str(self.model_path)
        }
    
    def validate_environment(self) -> bool:
        """
        验证运行环境是否满足插件要求
        
        Returns:
            环境是否满足要求
        """
        return True
    
    def get_requirements(self) -> List[str]:
        """
        获取插件依赖的包列表
        
        Returns:
            依赖包列表
        """
        return []
    
    # 新增：模型下载相关方法
    
    def get_downloadable_models(self) -> Dict[str, Dict[str, Any]]:
        """
        获取插件支持下载的模型列表
        
        Returns:
            模型信息字典，格式为:
            {
                "model_name": {
                    "size": "文件大小",
                    "description": "模型描述",
                    "download_urls": ["下载地址1", "下载地址2"],
                    "type": "模型类型",
                    "language": "支持语言",
                    "accuracy": "准确度",
                    "speed": "速度"
                }
            }
        """
        return {}
    
    def is_model_downloaded(self, model_name: str) -> bool:
        """
        检查模型是否已下载
        
        Args:
            model_name: 模型名称
            
        Returns:
            是否已下载
        """
        return False
    
    def download_model(self, model_name: str, progress_callback: Optional[Callable] = None) -> bool:
        """
        下载指定模型
        
        Args:
            model_name: 模型名称
            progress_callback: 进度回调函数，接收参数 (model_name, progress, status)
            
        Returns:
            下载是否成功
        """
        return False
    
    def delete_model(self, model_name: str) -> bool:
        """
        删除指定模型
        
        Args:
            model_name: 模型名称
            
        Returns:
            删除是否成功
        """
        return False
    
    def get_model_file_size(self, model_name: str) -> str:
        """
        获取模型文件大小
        
        Args:
            model_name: 模型名称
            
        Returns:
            文件大小字符串
        """
        return "未知"
    
    def __str__(self) -> str:
        return f"{self.plugin_name} v{self.plugin_version} ({self.model_size})"
    
    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}: {self.plugin_name} v{self.plugin_version}>"


class ModelWrapper(ABC):
    """模型包装器基类，用于统一不同模型的接口"""
    
    @abstractmethod
    def transcribe(self, audio, **kwargs):
        """转录音频"""
        pass
    
    def get_model_info(self) -> Dict[str, Any]:
        """获取模型信息"""
        return {}