"""
配置管理模块
用于管理用户的 API 设置和应用程序配置
提供配置校验、默认值管理和配置文件处理功能
"""

import json
import os
import yaml
from pathlib import Path
from typing import Dict, Any, Optional, List, Union
import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class ConfigValidationResult:
    """配置验证结果"""
    is_valid: bool
    errors: List[str]
    warnings: List[str]


class ConfigManager:
    """配置管理器"""
    
    def __init__(self, config_dir: Optional[str] = None):
        """
        初始化配置管理器
        
        Args:
            config_dir: 配置目录路径，默认为程序目录下的 config 文件夹
        """
        if config_dir is None:
            # 使用程序目录下的 config 文件夹
            self.config_dir = Path(__file__).parent.parent / "config"
        else:
            self.config_dir = Path(config_dir)
        
        self.config_file = self.config_dir / "config.json"
        self.default_config_file = Path(__file__).parent.parent / "config" / "default_config.json"
        
        # 确保配置目录存在
        self.config_dir.mkdir(parents=True, exist_ok=True)
        
        # 加载配置
        self.config = self._load_config()
    
    def _load_config(self) -> Dict[str, Any]:
        """加载配置文件"""
        try:
            # 如果用户配置文件存在，加载它
            if self.config_file.exists():
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    user_config = json.load(f)
                
                # 加载默认配置
                with open(self.default_config_file, 'r', encoding='utf-8') as f:
                    default_config = json.load(f)
                
                # 合并配置（用户配置覆盖默认配置）
                return self._merge_configs(default_config, user_config)
            else:
                # 如果用户配置文件不存在，使用默认配置
                with open(self.default_config_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
        
        except Exception as e:
            logger.error(f"加载配置文件失败: {e}")
            # 返回空配置
            return {}
    
    def _merge_configs(self, default: Dict[str, Any], user: Dict[str, Any]) -> Dict[str, Any]:
        """合并默认配置和用户配置"""
        result = default.copy()
        
        for key, value in user.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._merge_configs(result[key], value)
            else:
                result[key] = value
        
        return result
    
    def save_config(self) -> bool:
        """保存配置到文件"""
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=4, ensure_ascii=False)
            return True
        except Exception as e:
            logger.error(f"保存配置文件失败: {e}")
            return False
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        获取配置值
        
        Args:
            key: 配置键，支持点号分隔的嵌套键，如 'openai.api_key'
            default: 默认值
            
        Returns:
            配置值
        """
        keys = key.split('.')
        value = self.config
        
        try:
            for k in keys:
                value = value[k]
            return value
        except (KeyError, TypeError):
            return default
    
    def set(self, key: str, value: Any) -> bool:
        """
        设置配置值
        
        Args:
            key: 配置键，支持点号分隔的嵌套键
            value: 配置值
            
        Returns:
            是否设置成功
        """
        try:
            keys = key.split('.')
            config = self.config
            
            # 导航到目标位置
            for k in keys[:-1]:
                if k not in config:
                    config[k] = {}
                config = config[k]
            
            # 设置值
            config[keys[-1]] = value
            return True
        except Exception as e:
            logger.error(f"设置配置值失败: {e}")
            return False
    
    def get_openai_config(self) -> Dict[str, Any]:
        """获取 OpenAI 配置"""
        return self.get('translators.openai', {})
    
    def set_openai_api_key(self, api_key: str) -> bool:
        """设置 OpenAI API 密钥"""
        return self.set('translators.openai.api_key', api_key)
    
    def get_openai_api_key(self) -> str:
        """获取 OpenAI API 密钥"""
        return self.get('translators.openai.api_key', '')
    
    def get_translator_config(self, translator_name: str) -> Dict[str, Any]:
        """获取指定翻译器的配置"""
        return self.get(f'translators.{translator_name}', {})
    
    def is_translator_enabled(self, translator_name: str) -> bool:
        """检查翻译器是否启用"""
        return self.get(f'translators.{translator_name}.enabled', True)
    
    def set_translator_enabled(self, translator_name: str, enabled: bool) -> bool:
        """设置翻译器启用状态"""
        return self.set(f'translators.{translator_name}.enabled', enabled)
    
    def get_default_translator(self) -> str:
        """获取默认翻译器"""
        return self.get('general.default_translator', 'google')
    
    def set_default_translator(self, translator: str) -> bool:
        """设置默认翻译器"""
        return self.set('general.default_translator', translator)
    
    def get_fallback_translator(self) -> str:
        """获取备用翻译器"""
        return self.get('general.fallback_translator', 'simple')
    
    def set_fallback_translator(self, translator: str) -> bool:
        """设置备用翻译器"""
        return self.set('general.fallback_translator', translator)
    
    def get_whisper_config(self) -> Dict[str, Any]:
        """获取 Whisper 配置"""
        return self.get('whisper', {})
    
    def get_whisper_model_size(self) -> str:
        """获取 Whisper 模型大小"""
        return self.get('whisper.model_size', 'base')
    
    def get_available_whisper_models(self) -> List[str]:
        """获取所有可用的 Whisper 模型"""
        return ["tiny.en", "base.en", "small.en", "medium.en", 
                "tiny", "base", "small", "medium", "large"]
    
    def get_english_whisper_models(self) -> List[str]:
        """获取英语专用 Whisper 模型"""
        return ["tiny.en", "base.en", "small.en", "medium.en"]
    
    def get_multilingual_whisper_models(self) -> List[str]:
        """获取多语言 Whisper 模型"""
        return ["tiny", "base", "small", "medium", "large"]
    
    def is_english_model(self, model_size: str) -> bool:
        """检查是否为英语专用模型"""
        return model_size.endswith('.en')
    
    def get_model_recommendation(self, use_case: str = "general") -> str:
        """根据使用场景推荐模型"""
        recommendations = {
            "fast": "tiny.en" if self.get('whisper.language', 'auto') == 'en' else "tiny",
            "balanced": "base.en" if self.get('whisper.language', 'auto') == 'en' else "base", 
            "quality": "small.en" if self.get('whisper.language', 'auto') == 'en' else "small",
            "best": "medium.en" if self.get('whisper.language', 'auto') == 'en' else "large"
        }
        return recommendations.get(use_case, "base")
    
    def set_whisper_model_size(self, model_size: str) -> bool:
        """设置 Whisper 模型大小"""
        return self.set('whisper.model_size', model_size)
    
    def get_whisper_language(self) -> str:
        """获取 Whisper 语言设置"""
        return self.get('whisper.language', 'auto')
    
    def set_whisper_language(self, language: str) -> bool:
        """设置 Whisper 语言"""
        return self.set('whisper.language', language)
    
    def get_whisper_model_path(self) -> str:
        """获取 Whisper 模型存储路径"""
        model_path = self.get('whisper.model_path')
        if model_path:
            return model_path
        else:
            # 默认使用项目目录下的model文件夹
            project_root = Path(__file__).parent.parent
            default_path = str(project_root / "model")
            # 确保目录存在
            Path(default_path).mkdir(exist_ok=True)
            return default_path
    
    def set_whisper_model_path(self, model_path: str) -> bool:
        """设置 Whisper 模型存储路径"""
        return self.set('whisper.model_path', model_path)
    
    def get_whisper_device(self) -> str:
        """获取 Whisper 设备设置"""
        return self.get('whisper.device', 'auto')
    
    def set_whisper_device(self, device: str) -> bool:
        """设置 Whisper 设备"""
        return self.set('whisper.device', device)
    
    def is_intel_gpu_enabled(self) -> bool:
        """检查是否启用Intel显卡"""
        return self.get('whisper.enable_intel_gpu', False)
    
    def set_intel_gpu_enabled(self, enabled: bool) -> bool:
        """设置Intel显卡启用状态"""
        return self.set('whisper.enable_intel_gpu', enabled)
    
    def get_available_translators(self) -> list:
        """获取可用的翻译器列表"""
        translators = []
        
        # 检查各个翻译器的可用性
        if self.is_translator_enabled('google'):
            translators.append('google')
        
        if self.is_translator_enabled('openai') and self.get_openai_api_key():
            translators.append('openai')
        
        if self.is_translator_enabled('offline'):
            translators.append('offline')
        
        if self.is_translator_enabled('baidu') and self.get('translators.baidu.app_id') and self.get('translators.baidu.secret_key'):
            translators.append('baidu')
        
        if self.is_translator_enabled('tencent') and self.get('translators.tencent.secret_id') and self.get('translators.tencent.secret_key'):
            translators.append('tencent')
        
        if self.is_translator_enabled('aliyun') and self.get('translators.aliyun.access_key_id') and self.get('translators.aliyun.access_key_secret'):
            translators.append('aliyun')
        
        # 简单翻译器总是可用
        if self.is_translator_enabled('simple'):
            translators.append('simple')
        
        return translators
    
    def validate_config(self, config_data: Optional[Dict[str, Any]] = None) -> ConfigValidationResult:
        """
        验证配置数据
        
        Args:
            config_data: 要验证的配置数据，None表示验证当前配置
            
        Returns:
            配置验证结果
        """
        if config_data is None:
            config_data = self.config
        
        errors = []
        warnings = []
        
        try:
            # 验证转录器配置
            if 'transcriber' in config_data:
                transcriber_config = config_data['transcriber']
                
                # 验证模型名称
                if 'model_size' in transcriber_config:
                    valid_models = self.get_available_whisper_models()
                    if transcriber_config['model_size'] not in valid_models:
                        errors.append(f"无效的模型名称: {transcriber_config['model_size']}")
                
                # 验证语言代码
                if 'language' in transcriber_config and transcriber_config['language']:
                    # 这里可以添加语言代码验证逻辑
                    pass
            
            # 验证翻译器配置
            if 'translator' in config_data:
                translator_config = config_data['translator']
                
                # 验证默认翻译器
                if 'default' in translator_config:
                    available = self.get_available_translators()
                    if translator_config['default'] not in [t['name'] for t in available]:
                        errors.append(f"无效的默认翻译器: {translator_config['default']}")
                
                # 验证备用翻译器
                if 'fallback' in translator_config:
                    available = self.get_available_translators()
                    if translator_config['fallback'] not in [t['name'] for t in available]:
                        warnings.append(f"无效的备用翻译器: {translator_config['fallback']}")
                
                # 验证API密钥
                if 'openai' in translator_config:
                    openai_config = translator_config['openai']
                    if openai_config.get('enabled', False) and not openai_config.get('api_key'):
                        warnings.append("OpenAI翻译器已启用但未设置API密钥")
            
            # 验证输出格式配置
            if 'output' in config_data:
                output_config = config_data['output']
                
                # 验证编码
                if 'encoding' in output_config:
                    try:
                        'test'.encode(output_config['encoding'])
                    except LookupError:
                        errors.append(f"无效的编码: {output_config['encoding']}")
                
                # 验证格式
                if 'format' in output_config:
                    valid_formats = ['srt', 'webvtt', 'ass']
                    if output_config['format'] not in valid_formats:
                        errors.append(f"无效的输出格式: {output_config['format']}")
            
            return ConfigValidationResult(
                is_valid=len(errors) == 0,
                errors=errors,
                warnings=warnings
            )
            
        except Exception as e:
            logger.error(f"配置验证失败: {e}")
            return ConfigValidationResult(
                is_valid=False,
                errors=[f"配置验证异常: {e}"],
                warnings=[]
            )
    
    def get_config_schema(self) -> Dict[str, Any]:
        """
        获取配置模式定义
        
        Returns:
            配置模式字典
        """
        return {
            "transcriber": {
                "model_size": {
                    "type": "string",
                    "enum": self.get_available_whisper_models(),
                    "default": "base",
                    "description": "Whisper模型大小"
                },
                "language": {
                    "type": "string",
                    "default": "auto",
                    "description": "转录语言，auto表示自动检测"
                },
                "model_path": {
                    "type": "string",
                    "default": "",
                    "description": "自定义模型路径"
                }
            },
            "translator": {
                "default": {
                    "type": "string",
                    "enum": [t['name'] for t in self.get_available_translators()],
                    "default": "google",
                    "description": "默认翻译器"
                },
                "fallback": {
                    "type": "string",
                    "enum": [t['name'] for t in self.get_available_translators()],
                    "default": "simple",
                    "description": "备用翻译器"
                },
                "openai": {
                    "type": "object",
                    "properties": {
                        "enabled": {"type": "boolean", "default": False},
                        "api_key": {"type": "string", "default": ""},
                        "model": {"type": "string", "default": "gpt-3.5-turbo"},
                        "base_url": {"type": "string", "default": ""}
                    }
                }
            },
            "output": {
                "format": {
                    "type": "string",
                    "enum": ["srt", "webvtt", "ass"],
                    "default": "srt",
                    "description": "输出格式"
                },
                "encoding": {
                    "type": "string",
                    "default": "utf-8",
                    "description": "文件编码"
                }
            }
        }
    
    def apply_defaults(self, config_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        应用默认值到配置数据
        
        Args:
            config_data: 配置数据
            
        Returns:
            应用默认值后的配置数据
        """
        schema = self.get_config_schema()
        result = config_data.copy()
        
        def apply_defaults_recursive(data: Dict[str, Any], schema_part: Dict[str, Any]):
            for key, schema_info in schema_part.items():
                if key not in data:
                    if isinstance(schema_info, dict) and 'default' in schema_info:
                        data[key] = schema_info['default']
                    elif isinstance(schema_info, dict) and 'type' in schema_info and schema_info['type'] == 'object':
                        data[key] = {}
                
                if key in data and isinstance(schema_info, dict) and 'properties' in schema_info:
                    if not isinstance(data[key], dict):
                        data[key] = {}
                    apply_defaults_recursive(data[key], schema_info['properties'])
        
        apply_defaults_recursive(result, schema)
        return result
        """重置为默认配置"""
        try:
            with open(self.default_config_file, 'r', encoding='utf-8') as f:
                self.config = json.load(f)
            return self.save_config()
        except Exception as e:
            logger.error(f"重置配置失败: {e}")
            return False
    
    def export_config(self, file_path: str) -> bool:
        """导出配置到指定文件"""
        try:
            export_path = Path(file_path)
            with open(export_path, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=4, ensure_ascii=False)
            return True
        except Exception as e:
            logger.error(f"导出配置失败: {e}")
            return False
    
    def import_config(self, file_path: str) -> bool:
        """从指定文件导入配置"""
        try:
            import_path = Path(file_path)
            if not import_path.exists():
                logger.error(f"配置文件不存在: {file_path}")
                return False
            
            with open(import_path, 'r', encoding='utf-8') as f:
                imported_config = json.load(f)
            
            # 验证配置格式
            if not isinstance(imported_config, dict):
                logger.error("配置文件格式错误")
                return False
            
            self.config = imported_config
            return self.save_config()
        except Exception as e:
            logger.error(f"导入配置失败: {e}")
            return False


# 全局配置管理器实例
config_manager = ConfigManager()
