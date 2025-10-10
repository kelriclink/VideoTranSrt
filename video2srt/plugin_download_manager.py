"""
插件化模型下载管理器
统一管理所有插件的模型下载功能
"""

import os
import sys
from pathlib import Path
from typing import Dict, List, Any, Optional, Callable
import importlib
import inspect

# 添加项目根目录到Python路径
current_dir = Path(__file__).parent
project_root = current_dir.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from video2srt.plugins.base import BaseModelLoaderPlugin


class PluginDownloadManager:
    """插件化下载管理器"""
    
    def __init__(self, plugins_dir: Optional[Path] = None):
        """
        初始化插件下载管理器
        
        Args:
            plugins_dir: 插件目录路径，默认为当前目录下的plugins文件夹
        """
        self.plugins_dir = plugins_dir or (Path(__file__).parent / "plugins")
        self.plugins: Dict[str, BaseModelLoaderPlugin] = {}
        self.available_models: Dict[str, Dict[str, Any]] = {}
        self._load_plugins()
        self._collect_available_models()
    
    def _load_plugins(self):
        """加载所有插件"""
        if not self.plugins_dir.exists():
            print(f"插件目录不存在: {self.plugins_dir}")
            return
        
        for plugin_dir in self.plugins_dir.iterdir():
            if not plugin_dir.is_dir() or plugin_dir.name.startswith('_'):
                continue
            
            plugin_file = plugin_dir / "plugin.py"
            if not plugin_file.exists():
                continue
            
            try:
                # 动态导入插件模块
                module_name = f"video2srt.plugins.{plugin_dir.name}.plugin"
                spec = importlib.util.spec_from_file_location(module_name, plugin_file)
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                
                # 查找插件类
                for name, obj in inspect.getmembers(module):
                    if (inspect.isclass(obj) and 
                        issubclass(obj, BaseModelLoaderPlugin) and 
                        obj != BaseModelLoaderPlugin):
                        
                        # 实例化插件 - 使用默认参数
                        plugin_instance = obj("base")  # 使用默认model_size
                        self.plugins[plugin_instance.plugin_name] = plugin_instance
                        print(f"已加载插件: {plugin_instance.plugin_name}")
                        break
                        
            except Exception as e:
                print(f"加载插件失败 {plugin_dir.name}: {e}")
    
    def _collect_available_models(self):
        """收集所有插件的可用模型"""
        self.available_models.clear()
        
        for plugin_name, plugin in self.plugins.items():
            try:
                if hasattr(plugin, 'get_downloadable_models'):
                    models = plugin.get_downloadable_models()
                    for model_name, model_info in models.items():
                        # 添加插件信息
                        model_info_with_plugin = model_info.copy()
                        model_info_with_plugin['plugin_name'] = plugin_name
                        model_info_with_plugin['plugin_version'] = plugin.plugin_version
                        
                        # 检查模型是否已下载
                        if hasattr(plugin, 'is_model_downloaded'):
                            model_info_with_plugin['is_downloaded'] = plugin.is_model_downloaded(model_name)
                        else:
                            model_info_with_plugin['is_downloaded'] = False
                        
                        # 获取模型文件大小
                        if hasattr(plugin, 'get_model_file_size'):
                            model_info_with_plugin['actual_size'] = plugin.get_model_file_size(model_name)
                        
                        self.available_models[model_name] = model_info_with_plugin
                        
            except Exception as e:
                print(f"收集插件 {plugin_name} 的模型信息失败: {e}")
    
    def get_all_available_models(self) -> Dict[str, Dict[str, Any]]:
        """获取所有可用的模型"""
        return self.available_models.copy()
    
    def get_all_models(self) -> Dict[str, Dict[str, Any]]:
        """获取所有模型（别名方法）"""
        return self.get_all_available_models()
    
    def get_models_by_plugin(self, plugin_name: str) -> Dict[str, Dict[str, Any]]:
        """获取指定插件的模型"""
        return {
            model_name: model_info 
            for model_name, model_info in self.available_models.items()
            if model_info.get('plugin_name') == plugin_name
        }
    
    def is_model_downloaded(self, model_name: str) -> bool:
        """检查模型是否已下载"""
        if model_name not in self.available_models:
            return False
        
        plugin_name = self.available_models[model_name]['plugin_name']
        plugin = self.plugins.get(plugin_name)
        
        if plugin and hasattr(plugin, 'is_model_downloaded'):
            return plugin.is_model_downloaded(model_name)
        
        return False
    
    def download_model(self, model_name: str, progress_callback: Optional[Callable] = None) -> bool:
        """
        下载指定模型
        
        Args:
            model_name: 模型名称
            progress_callback: 进度回调函数，参数为 (model_name, progress, message)
        
        Returns:
            bool: 下载是否成功
        """
        if model_name not in self.available_models:
            if progress_callback:
                progress_callback(model_name, 0, f"未找到模型: {model_name}")
            return False
        
        plugin_name = self.available_models[model_name]['plugin_name']
        plugin = self.plugins.get(plugin_name)
        
        if not plugin:
            if progress_callback:
                progress_callback(model_name, 0, f"插件未找到: {plugin_name}")
            return False
        
        if not hasattr(plugin, 'download_model'):
            if progress_callback:
                progress_callback(model_name, 0, f"插件 {plugin_name} 不支持下载功能")
            return False
        
        try:
            success = plugin.download_model(model_name, progress_callback)
            if success:
                # 更新模型状态
                self.available_models[model_name]['is_downloaded'] = True
                if hasattr(plugin, 'get_model_file_size'):
                    self.available_models[model_name]['actual_size'] = plugin.get_model_file_size(model_name)
            return success
        except Exception as e:
            if progress_callback:
                progress_callback(model_name, 0, f"下载失败: {str(e)}")
            return False
    
    def delete_model(self, model_name: str) -> bool:
        """删除指定模型"""
        if model_name not in self.available_models:
            return False
        
        plugin_name = self.available_models[model_name]['plugin_name']
        plugin = self.plugins.get(plugin_name)
        
        if not plugin or not hasattr(plugin, 'delete_model'):
            return False
        
        try:
            success = plugin.delete_model(model_name)
            if success:
                # 更新模型状态
                self.available_models[model_name]['is_downloaded'] = False
                self.available_models[model_name]['actual_size'] = self.available_models[model_name].get('size', '未知')
            return success
        except Exception as e:
            print(f"删除模型失败: {e}")
            return False
    
    def get_model_info(self, model_name: str) -> Optional[Dict[str, Any]]:
        """获取指定模型的详细信息"""
        return self.available_models.get(model_name)
    
    def refresh_models(self):
        """刷新模型列表"""
        self._collect_available_models()
    
    def get_plugin_list(self) -> List[str]:
        """获取已加载的插件列表"""
        return list(self.plugins.keys())
    
    def get_plugin_info(self, plugin_name: str) -> Optional[Dict[str, Any]]:
        """获取插件信息"""
        plugin = self.plugins.get(plugin_name)
        if plugin:
            return {
                'name': plugin.plugin_name,
                'version': plugin.plugin_version,
                'supported_models': plugin.supported_models,
                'has_download_support': hasattr(plugin, 'download_model')
            }
        return None
    
    def get_available_plugins(self) -> Dict[str, Dict[str, Any]]:
        """获取所有可用插件的信息"""
        plugin_info = {}
        for plugin_name, plugin in self.plugins.items():
            plugin_info[plugin_name] = {
                'name': plugin.plugin_name,
                'version': getattr(plugin, 'plugin_version', '1.0.0'),
                'models': list(plugin.get_downloadable_models().keys())
            }
        return plugin_info
    
    def get_model_path(self) -> str:
        """获取模型存储路径"""
        # 从第一个插件获取模型路径，所有插件应该使用相同的基础路径
        if self.plugins:
            first_plugin = next(iter(self.plugins.values()))
            return str(first_plugin.model_path)
        
        # 如果没有插件，返回默认路径
        project_root = Path(__file__).parent.parent
        return str(project_root / "model")


# 全局实例
_download_manager = None

def get_download_manager() -> PluginDownloadManager:
    """获取全局下载管理器实例"""
    global _download_manager
    if _download_manager is None:
        _download_manager = PluginDownloadManager()
    return _download_manager


if __name__ == "__main__":
    # 测试代码
    manager = PluginDownloadManager()
    
    print("已加载的插件:")
    for plugin_name in manager.get_plugin_list():
        print(f"  - {plugin_name}")
    
    print("\n可用的模型:")
    for model_name, model_info in manager.get_all_available_models().items():
        status = "已下载" if model_info['is_downloaded'] else "未下载"
        print(f"  - {model_name} ({model_info['plugin_name']}) - {status}")