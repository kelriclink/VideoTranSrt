"""
模型加载器模块 - 插件化版本
为不同类型的Whisper模型提供插件化的加载器系统
"""

# 导入插件系统
from .plugins import BaseModelLoaderPlugin, PluginManager
from .model_loader_factory import ModelLoaderFactory, create_loader

# 为了向后兼容，保留原有的接口
class ModelLoaderFactory:
    """模型加载器工厂 - 向后兼容接口"""
    
    @staticmethod
    def create_loader(model_size: str, model_path: str = None, device: str = "cpu"):
        """
        创建模型加载器（向后兼容的静态方法）
        
        Args:
            model_size: 模型大小/名称
            model_path: 模型路径
            device: 设备类型
            
        Returns:
            模型加载器插件实例
        """
        return create_loader(model_size, model_path, device)

# 导出主要接口
__all__ = [
    'BaseModelLoaderPlugin',
    'PluginManager', 
    'ModelLoaderFactory',
    'create_loader'
]