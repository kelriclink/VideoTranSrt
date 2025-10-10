"""
插件管理器
负责插件的发现、加载、管理和调度
"""

import os
import importlib
import importlib.util
import inspect
from pathlib import Path
from typing import Dict, List, Optional, Type, Any
from .base import BaseModelLoaderPlugin


class PluginManager:
    """插件管理器"""
    
    def __init__(self, plugin_dirs: Optional[List[str]] = None):
        """
        初始化插件管理器
        
        Args:
            plugin_dirs: 插件目录列表，None表示使用默认目录
        """
        self._plugins: Dict[str, Type[BaseModelLoaderPlugin]] = {}
        self._loaded_instances: Dict[str, BaseModelLoaderPlugin] = {}
        
        # 设置插件目录
        if plugin_dirs is None:
            # 新的目录结构：每个加载器一个文件夹
            base_dir = Path(__file__).parent
            plugin_dirs = []
            
            # 扫描所有插件文件夹
            for item in base_dir.iterdir():
                if (item.is_dir() and 
                    not item.name.startswith('_') and 
                    item.name not in ['__pycache__', 'loaders']):
                    plugin_dirs.append(str(item))
            
            # 保持对旧loaders目录的兼容性
            old_loaders_dir = base_dir / "loaders"
            if old_loaders_dir.exists():
                plugin_dirs.append(str(old_loaders_dir))
        
        self.plugin_dirs = [Path(d) for d in plugin_dirs]
        
        # 自动发现和注册插件
        self.discover_plugins()
    
    def discover_plugins(self):
        """发现并注册所有插件"""
        for plugin_dir in self.plugin_dirs:
            if not plugin_dir.exists():
                continue
                
            # 检查是否是新的目录结构（包含plugin.py）
            plugin_file = plugin_dir / "plugin.py"
            if plugin_file.exists():
                try:
                    self._load_plugin_from_file(plugin_file)
                except Exception as e:
                    print(f"加载插件失败 {plugin_file}: {e}")
            else:
                # 旧的目录结构：扫描所有.py文件
                for plugin_file in plugin_dir.glob("*.py"):
                    if plugin_file.name.startswith("_"):
                        continue
                        
                    try:
                        self._load_plugin_from_file(plugin_file)
                    except Exception as e:
                        print(f"加载插件失败 {plugin_file}: {e}")
    
    def _load_plugin_from_file(self, plugin_file: Path):
        """从文件加载插件"""
        # 构建模块名
        if plugin_file.name == "plugin.py":
            # 新的目录结构：video2srt.plugins.plugin_name.plugin
            plugin_name = plugin_file.parent.name
            module_name = f"video2srt.plugins.{plugin_name}.plugin"
        else:
            # 旧的目录结构：video2srt.plugins.loaders.file_name
            module_name = f"video2srt.plugins.loaders.{plugin_file.stem}"
        
        try:
            # 动态导入模块
            spec = importlib.util.spec_from_file_location(module_name, plugin_file)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            
            # 查找插件类
            for name, obj in inspect.getmembers(module):
                if (inspect.isclass(obj) and 
                    issubclass(obj, BaseModelLoaderPlugin) and 
                    obj != BaseModelLoaderPlugin):
                    
                    # 注册插件
                    plugin_name = obj.plugin_name if hasattr(obj, 'plugin_name') else name
                    self._plugins[plugin_name] = obj
                    print(f"发现插件: {plugin_name}")
                    
        except Exception as e:
            raise RuntimeError(f"无法加载插件文件 {plugin_file}: {e}")
    
    def register_plugin(self, plugin_class: Type[BaseModelLoaderPlugin]):
        """
        手动注册插件类
        
        Args:
            plugin_class: 插件类
        """
        if not issubclass(plugin_class, BaseModelLoaderPlugin):
            raise ValueError("插件类必须继承自BaseModelLoaderPlugin")
        
        plugin_name = plugin_class.plugin_name
        self._plugins[plugin_name] = plugin_class
        print(f"注册插件: {plugin_name}")
    
    def get_plugin_for_model(self, model_size: str) -> Optional[Type[BaseModelLoaderPlugin]]:
        """
        根据模型大小获取合适的插件类
        
        Args:
            model_size: 模型大小/名称
            
        Returns:
            插件类，如果没有找到返回None
        """
        for plugin_name, plugin_class in self._plugins.items():
            try:
                # 创建临时实例来检查支持性
                temp_instance = plugin_class(model_size)
                if temp_instance.is_supported(model_size):
                    return plugin_class
            except Exception as e:
                print(f"检查插件 {plugin_name} 支持性时出错: {e}")
                continue
        
        return None
    
    def create_loader(self, model_size: str, model_path: Optional[str] = None, **kwargs) -> BaseModelLoaderPlugin:
        """
        创建模型加载器实例
        
        Args:
            model_size: 模型大小/名称
            model_path: 模型路径
            **kwargs: 其他参数
            
        Returns:
            模型加载器实例
            
        Raises:
            ValueError: 如果没有找到支持的插件
        """
        plugin_class = self.get_plugin_for_model(model_size)
        
        if plugin_class is None:
            raise ValueError(f"没有找到支持模型 '{model_size}' 的插件")
        
        # 创建插件实例
        instance = plugin_class(model_size, model_path, **kwargs)
        
        # 验证环境
        if not instance.validate_environment():
            raise RuntimeError(f"插件 {instance.plugin_name} 的运行环境不满足要求")
        
        return instance
    
    def get_supported_models(self) -> Dict[str, List[str]]:
        """
        获取所有插件支持的模型列表
        
        Returns:
            插件名称到支持模型列表的映射
        """
        supported = {}
        for plugin_name, plugin_class in self._plugins.items():
            try:
                # 创建临时实例获取支持的模型
                temp_instance = plugin_class("dummy")
                supported[plugin_name] = temp_instance.supported_models
            except Exception:
                supported[plugin_name] = []
        
        return supported
    
    def get_plugin_info(self) -> List[Dict[str, Any]]:
        """
        获取所有插件的信息
        
        Returns:
            插件信息列表
        """
        info_list = []
        for plugin_name, plugin_class in self._plugins.items():
            try:
                temp_instance = plugin_class("dummy")
                info = temp_instance.get_plugin_info()
                info_list.append(info)
            except Exception as e:
                info_list.append({
                    "name": plugin_name,
                    "error": str(e)
                })
        
        return info_list
    
    def list_plugins(self) -> List[str]:
        """
        列出所有已注册的插件名称
        
        Returns:
            插件名称列表
        """
        return list(self._plugins.keys())
    
    def has_plugin(self, plugin_name: str) -> bool:
        """
        检查是否存在指定名称的插件
        
        Args:
            plugin_name: 插件名称
            
        Returns:
            是否存在该插件
        """
        return plugin_name in self._plugins
    
    def reload_plugins(self):
        """重新加载所有插件"""
        self._plugins.clear()
        self._loaded_instances.clear()
        self.discover_plugins()


# 全局插件管理器实例
plugin_manager = PluginManager()