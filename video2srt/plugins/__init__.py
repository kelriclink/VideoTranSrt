"""
模型加载器插件系统
"""

from .base import BaseModelLoaderPlugin
from .manager import PluginManager

__all__ = ['BaseModelLoaderPlugin', 'PluginManager']