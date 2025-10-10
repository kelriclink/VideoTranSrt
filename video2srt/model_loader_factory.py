"""
新的模型加载器工厂
使用插件系统来管理不同类型的模型加载器
"""

from typing import Optional
from .plugins import PluginManager, BaseModelLoaderPlugin
from .plugins.manager import plugin_manager


class ModelLoaderFactory:
    """模型加载器工厂 - 使用插件系统"""
    
    def __init__(self, plugin_manager_instance: Optional[PluginManager] = None):
        """
        初始化工厂
        
        Args:
            plugin_manager_instance: 插件管理器实例，None表示使用全局实例
        """
        self.plugin_manager = plugin_manager_instance or plugin_manager
    
    def create_loader(self, model_size: str, model_path: Optional[str] = None, 
                     device: str = "cpu", **kwargs) -> BaseModelLoaderPlugin:
        """
        根据模型类型创建相应的加载器
        
        Args:
            model_size: 模型大小/名称
            model_path: 模型路径
            device: 设备类型
            **kwargs: 其他参数
            
        Returns:
            模型加载器插件实例
            
        Raises:
            ValueError: 如果没有找到支持的插件
        """
        # 将device参数传递给插件
        kwargs['device'] = device
        
        return self.plugin_manager.create_loader(
            model_size=model_size,
            model_path=model_path,
            **kwargs
        )
    
    def get_supported_models(self):
        """获取所有支持的模型"""
        return self.plugin_manager.get_supported_models()
    
    def list_plugins(self):
        """列出所有可用的插件"""
        return self.plugin_manager.list_plugins()
    
    def get_plugin_info(self):
        """获取插件信息"""
        return self.plugin_manager.get_plugin_info()


# 保持向后兼容性的静态方法
def create_loader(model_size: str, model_path: Optional[str] = None, device: str = "cpu"):
    """
    创建模型加载器（向后兼容的静态方法）
    
    Args:
        model_size: 模型大小/名称
        model_path: 模型路径
        device: 设备类型
        
    Returns:
        模型加载器插件实例
    """
    factory = ModelLoaderFactory()
    return factory.create_loader(model_size, model_path, device)