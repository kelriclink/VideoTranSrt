"""
翻译器管理模块
实现翻译器重试机制、自动降级和负载均衡
"""

import time
import random
from typing import List, Dict, Any, Optional, Callable
from dataclasses import dataclass
from enum import Enum
import logging

from .models import Segment, TranslationResult
from .translator import get_translator, Translator, get_available_translators
from .config_manager import config_manager, ConfigValidationResult
from .reporter import Reporter

logger = logging.getLogger(__name__)


class TranslatorStatus(Enum):
    """翻译器状态"""
    AVAILABLE = "available"
    DEGRADED = "degraded"  # 降级状态，可用但性能差
    UNAVAILABLE = "unavailable"
    RATE_LIMITED = "rate_limited"
    CONFIG_ERROR = "config_error"  # 配置错误


@dataclass
class TranslatorConfig:
    """翻译器配置"""
    enabled: bool = True
    timeout: int = 15
    retry_count: int = 3
    max_requests_per_minute: int = 60
    priority: int = 1  # 优先级，数字越小优先级越高
    
    def validate(self) -> List[str]:
        """验证配置"""
        errors = []
        if self.timeout <= 0:
            errors.append("timeout必须大于0")
        if self.retry_count < 0:
            errors.append("retry_count不能为负数")
        if self.max_requests_per_minute <= 0:
            errors.append("max_requests_per_minute必须大于0")
        if self.priority < 0:
            errors.append("priority不能为负数")
        return errors


@dataclass
class TranslatorInfo:
    """翻译器信息"""
    name: str
    translator: Optional[Translator]
    status: TranslatorStatus
    config: TranslatorConfig = None
    error_count: int = 0
    last_error_time: Optional[float] = None
    success_count: int = 0
    total_requests: int = 0
    avg_response_time: float = 0.0
    last_request_time: Optional[float] = None
    requests_in_current_minute: int = 0
    
    def __post_init__(self):
        if self.config is None:
            self.config = TranslatorConfig()
    
    @property
    def success_rate(self) -> float:
        """成功率"""
        if self.total_requests == 0:
            return 0.0
        return self.success_count / self.total_requests
    
    @property
    def is_healthy(self) -> bool:
        """是否健康"""
        # 初始阶段（尚未请求过）应视为健康，以便完成首次尝试
        if not self.config.enabled:
            return False
        if self.status not in [TranslatorStatus.AVAILABLE, TranslatorStatus.DEGRADED]:
            return False
        if self.total_requests == 0:
            return True
        # 对已有历史的翻译器，要求成功率达到阈值
        return self.success_rate >= 0.5
    
    @property
    def is_rate_limited(self) -> bool:
        """是否受速率限制"""
        if not self.last_request_time:
            return False
        
        current_time = time.time()
        # 如果距离上次请求超过1分钟，重置计数
        if current_time - self.last_request_time > 60:
            self.requests_in_current_minute = 0
            return False
        
        return self.requests_in_current_minute >= self.config.max_requests_per_minute


class TranslatorManager:
    """翻译器管理器"""
    
    # 默认配置
    DEFAULT_RETRY_CONFIG = {
        'max_retries': 3,
        'base_delay': 1.0,  # 基础延迟（秒）
        'max_delay': 30.0,  # 最大延迟（秒）
        'backoff_factor': 2.0,  # 退避因子
        'jitter': True  # 是否添加随机抖动
    }
    
    DEFAULT_CIRCUIT_BREAKER_CONFIG = {
        'failure_threshold': 5,  # 失败阈值
        'recovery_timeout': 300,  # 恢复超时（秒）
        'half_open_max_calls': 3  # 半开状态最大调用次数
    }
    
    def __init__(self, reporter: Optional[Reporter] = None):
        """
        初始化翻译器管理器
        
        Args:
            reporter: 日志报告器
        """
        self.reporter = reporter or Reporter()
        self.translators: Dict[str, TranslatorInfo] = {}
        
        # 从配置管理器获取配置，如果不存在则使用默认值
        self.retry_config = self._get_retry_config()
        self.circuit_breaker_config = self._get_circuit_breaker_config()
        
        # 配置校验结果缓存
        self._config_validation_cache: Dict[str, ConfigValidationResult] = {}
        
        self._initialize_translators()
    
    def _get_retry_config(self) -> Dict[str, Any]:
        """获取重试配置"""
        config = config_manager.get('translator_manager.retry', {})
        return {**self.DEFAULT_RETRY_CONFIG, **config}
    
    def _get_circuit_breaker_config(self) -> Dict[str, Any]:
        """获取熔断器配置"""
        config = config_manager.get('translator_manager.circuit_breaker', {})
        return {**self.DEFAULT_CIRCUIT_BREAKER_CONFIG, **config}
    
    def _load_translator_config(self, translator_name: str) -> TranslatorConfig:
        """加载翻译器配置"""
        config_data = config_manager.get_translator_config(translator_name)
        
        # 创建配置对象，使用默认值填充缺失的字段
        return TranslatorConfig(
            enabled=config_data.get('enabled', True),
            timeout=config_data.get('timeout', 15),
            retry_count=config_data.get('retry_count', 3),
            max_requests_per_minute=config_data.get('max_requests_per_minute', 60),
            priority=config_data.get('priority', 1)
        )
    
    def validate_translator_config(self, translator_name: str) -> ConfigValidationResult:
        """
        验证翻译器配置
        
        Args:
            translator_name: 翻译器名称
            
        Returns:
            配置验证结果
        """
        # 检查缓存
        if translator_name in self._config_validation_cache:
            return self._config_validation_cache[translator_name]
        
        errors = []
        warnings = []
        
        try:
            # 检查翻译器是否在可用列表中
            available_translators = get_available_translators()
            if translator_name not in available_translators:
                errors.append(f"翻译器 '{translator_name}' 不在可用翻译器列表中")
            
            # 加载并验证配置
            config = self._load_translator_config(translator_name)
            config_errors = config.validate()
            errors.extend(config_errors)
            
            # 检查特定翻译器的配置要求
            translator_config = config_manager.get_translator_config(translator_name)
            
            if translator_name == 'openai':
                if not translator_config.get('api_key'):
                    errors.append("OpenAI翻译器需要配置api_key")
                if not translator_config.get('base_url'):
                    warnings.append("OpenAI翻译器未配置base_url，将使用默认值")
            
            elif translator_name == 'baidu':
                if not translator_config.get('app_id') or not translator_config.get('secret_key'):
                    errors.append("百度翻译器需要配置app_id和secret_key")
            
            elif translator_name == 'tencent':
                if not translator_config.get('secret_id') or not translator_config.get('secret_key'):
                    errors.append("腾讯翻译器需要配置secret_id和secret_key")
            
            elif translator_name == 'aliyun':
                if not translator_config.get('access_key_id') or not translator_config.get('access_key_secret'):
                    errors.append("阿里云翻译器需要配置access_key_id和access_key_secret")
            
        except Exception as e:
            errors.append(f"配置验证过程中发生错误: {str(e)}")
        
        result = ConfigValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings
        )
        
        # 缓存结果
        self._config_validation_cache[translator_name] = result
        
        return result
    
    def _initialize_translators(self):
        """初始化所有可用的翻译器"""
        available_translators = get_available_translators()
        
        for translator_name in available_translators:
            try:
                # 验证配置
                validation_result = self.validate_translator_config(translator_name)
                
                if not validation_result.is_valid:
                    self.translators[translator_name] = TranslatorInfo(
                        name=translator_name,
                        translator=None,
                        status=TranslatorStatus.CONFIG_ERROR,
                        config=self._load_translator_config(translator_name)
                    )
                    self.reporter.error(f"翻译器 {translator_name} 配置错误: {', '.join(validation_result.errors)}")
                    continue
                
                # 记录警告
                for warning in validation_result.warnings:
                    self.reporter.warning(f"翻译器 {translator_name}: {warning}")
                
                # 初始化翻译器
                translator = get_translator(translator_name)
                config = self._load_translator_config(translator_name)
                
                self.translators[translator_name] = TranslatorInfo(
                    name=translator_name,
                    translator=translator,
                    status=TranslatorStatus.AVAILABLE if config.enabled else TranslatorStatus.UNAVAILABLE,
                    config=config
                )
                self.reporter.debug(f"初始化翻译器: {translator_name}")
                
            except Exception as e:
                self.translators[translator_name] = TranslatorInfo(
                    name=translator_name,
                    translator=None,
                    status=TranslatorStatus.UNAVAILABLE,
                    config=self._load_translator_config(translator_name)
                )
                self.reporter.warning(f"翻译器 {translator_name} 初始化失败: {e}")
    
    def get_best_translator(self, exclude: Optional[List[str]] = None) -> Optional[str]:
        """
        获取最佳翻译器
        
        Args:
            exclude: 排除的翻译器列表
            
        Returns:
            最佳翻译器名称，如果没有可用翻译器则返回None
        """
        exclude = exclude or []
        
        # 过滤可用的翻译器
        available = [
            info for name, info in self.translators.items()
            if name not in exclude and info.is_healthy and not info.is_rate_limited
        ]
        
        if not available:
            return None
        
        # 按优先级、成功率和响应时间排序
        available.sort(key=lambda x: (x.config.priority, -x.success_rate, x.avg_response_time))
        
        return available[0].name
    
    def translate_with_retry(self, segments: List[Segment], target_language: str, 
                           source_language: str = "auto",
                           preferred_translator: Optional[str] = None) -> TranslationResult:
        """
        带重试机制的翻译
        
        Args:
            segments: 要翻译的字幕段
            target_language: 目标语言
            source_language: 源语言
            preferred_translator: 首选翻译器
            
        Returns:
            翻译结果
            
        Raises:
            Exception: 所有翻译器都失败时抛出异常
        """
        if not segments:
            return TranslationResult(
                segments=[],
                source_language=source_language,
                target_language=target_language,
                translator_name="none"
            )
        
        # 确定翻译器优先级列表
        translator_priority = self._get_translator_priority(preferred_translator)
        
        last_exception = None
        
        for translator_name in translator_priority:
            translator_info = self.translators.get(translator_name)
            if not translator_info or not translator_info.is_healthy:
                continue
            
            # 检查速率限制
            if translator_info.is_rate_limited:
                self.reporter.debug(f"翻译器 {translator_name} 受速率限制，跳过")
                continue
            
            try:
                result = self._translate_with_single_translator(
                    translator_info, segments, target_language, source_language
                )
                
                # 更新成功统计
                self._update_translator_stats(translator_name, success=True)
                
                return result
                
            except Exception as e:
                last_exception = e
                self.reporter.warning(f"翻译器 {translator_name} 失败: {e}")
                
                # 更新失败统计
                self._update_translator_stats(translator_name, success=False, error=e)
                
                # 继续尝试下一个翻译器
                continue
        
        # 所有翻译器都失败
        error_msg = f"所有翻译器都失败，最后错误: {last_exception}"
        self.reporter.error(error_msg)
        raise Exception(error_msg)
    
    def _translate_with_single_translator(self, translator_info: TranslatorInfo,
                                        segments: List[Segment], target_language: str,
                                        source_language: str) -> TranslationResult:
        """
        使用单个翻译器进行翻译（带重试）
        
        Args:
            translator_info: 翻译器信息
            segments: 字幕段
            target_language: 目标语言
            source_language: 源语言
            
        Returns:
            翻译结果
        """
        translator = translator_info.translator
        if not translator:
            raise Exception(f"翻译器 {translator_info.name} 未初始化")
        
        last_exception = None
        
        for attempt in range(self.retry_config['max_retries'] + 1):
            try:
                start_time = time.time()
                
                # 执行翻译
                result = translator.translate_segments(segments, target_language, source_language)
                
                # 更新响应时间
                response_time = time.time() - start_time
                self._update_response_time(translator_info.name, response_time)
                
                return result
                
            except Exception as e:
                last_exception = e
                
                if attempt < self.retry_config['max_retries']:
                    # 计算延迟时间
                    delay = self._calculate_retry_delay(attempt)
                    
                    self.reporter.debug(
                        f"翻译器 {translator_info.name} 第 {attempt + 1} 次尝试失败: {e}, "
                        f"{delay:.1f}秒后重试"
                    )
                    
                    time.sleep(delay)
                else:
                    # 最后一次尝试也失败了
                    self.reporter.warning(
                        f"翻译器 {translator_info.name} 重试 {self.retry_config['max_retries']} 次后仍然失败"
                    )
        
        raise last_exception
    
    def _get_translator_priority(self, preferred: Optional[str]) -> List[str]:
        """
        获取翻译器优先级列表
        
        Args:
            preferred: 首选翻译器
            
        Returns:
            按优先级排序的翻译器名称列表
        """
        priority_list = []
        
        # 首选翻译器
        if preferred and preferred in self.translators:
            priority_list.append(preferred)
        
        # 默认翻译器
        default_translator = config_manager.get_default_translator()
        if default_translator and default_translator not in priority_list:
            priority_list.append(default_translator)
        
        # 备用翻译器
        fallback_translator = config_manager.get_fallback_translator()
        if fallback_translator and fallback_translator not in priority_list:
            priority_list.append(fallback_translator)
        
        # 其他可用翻译器（按配置优先级和成功率排序）
        other_translators = [
            name for name in self.translators.keys()
            if name not in priority_list
        ]
        other_translators.sort(
            key=lambda x: (
                self.translators[x].config.priority,
                -self.translators[x].success_rate
            )
        )
        priority_list.extend(other_translators)
        
        return priority_list
    
    def _calculate_retry_delay(self, attempt: int) -> float:
        """
        计算重试延迟时间
        
        Args:
            attempt: 尝试次数（从0开始）
            
        Returns:
            延迟时间（秒）
        """
        delay = self.retry_config['base_delay'] * (
            self.retry_config['backoff_factor'] ** attempt
        )
        
        # 限制最大延迟
        delay = min(delay, self.retry_config['max_delay'])
        
        # 添加随机抖动
        if self.retry_config['jitter']:
            delay *= (0.5 + random.random() * 0.5)
        
        return delay
    
    def _update_translator_stats(self, translator_name: str, success: bool, 
                               error: Optional[Exception] = None):
        """
        更新翻译器统计信息
        
        Args:
            translator_name: 翻译器名称
            success: 是否成功
            error: 错误信息（如果失败）
        """
        if translator_name not in self.translators:
            return
        
        info = self.translators[translator_name]
        info.total_requests += 1
        info.last_request_time = time.time()
        
        if success:
            info.success_count += 1
            info.error_count = 0  # 重置错误计数
            info.requests_in_current_minute += 1
            
            # 如果之前是降级状态，可能需要恢复
            if info.status == TranslatorStatus.DEGRADED:
                if info.success_rate >= 0.8:  # 成功率恢复到80%以上
                    info.status = TranslatorStatus.AVAILABLE
                    self.reporter.info(f"翻译器 {translator_name} 已恢复正常状态")
        else:
            info.error_count += 1
            info.last_error_time = time.time()
            
            # 根据错误次数调整状态
            if info.error_count >= self.circuit_breaker_config['failure_threshold']:
                info.status = TranslatorStatus.UNAVAILABLE
                self.reporter.warning(f"翻译器 {translator_name} 已标记为不可用")
            elif info.success_rate < 0.7:  # 成功率低于70%
                info.status = TranslatorStatus.DEGRADED
                self.reporter.warning(f"翻译器 {translator_name} 已降级")
    
    def _update_response_time(self, translator_name: str, response_time: float):
        """
        更新翻译器响应时间
        
        Args:
            translator_name: 翻译器名称
            response_time: 响应时间（秒）
        """
        if translator_name not in self.translators:
            return
        
        info = self.translators[translator_name]
        
        # 使用指数移动平均计算平均响应时间
        alpha = 0.1  # 平滑因子
        if info.avg_response_time == 0:
            info.avg_response_time = response_time
        else:
            info.avg_response_time = (
                alpha * response_time + (1 - alpha) * info.avg_response_time
            )
    
    def reload_config(self):
        """重新加载配置"""
        self._config_validation_cache.clear()
        self.retry_config = self._get_retry_config()
        self.circuit_breaker_config = self._get_circuit_breaker_config()
        
        # 重新加载翻译器配置
        for name, info in self.translators.items():
            info.config = self._load_translator_config(name)
            
            # 重新验证配置
            validation_result = self.validate_translator_config(name)
            if not validation_result.is_valid:
                info.status = TranslatorStatus.CONFIG_ERROR
                self.reporter.error(f"翻译器 {name} 配置错误: {', '.join(validation_result.errors)}")
            elif info.status == TranslatorStatus.CONFIG_ERROR:
                # 如果之前是配置错误，现在配置正确了，恢复状态
                info.status = TranslatorStatus.AVAILABLE if info.config.enabled else TranslatorStatus.UNAVAILABLE
        
        self.reporter.info("翻译器管理器配置已重新加载")
    
    def get_translator_stats(self) -> Dict[str, Dict[str, Any]]:
        """
        获取所有翻译器的统计信息
        
        Returns:
            翻译器统计信息字典
        """
        stats = {}
        
        for name, info in self.translators.items():
            stats[name] = {
                'status': info.status.value,
                'success_rate': info.success_rate,
                'total_requests': info.total_requests,
                'success_count': info.success_count,
                'error_count': info.error_count,
                'avg_response_time': info.avg_response_time,
                'is_healthy': info.is_healthy,
                'is_rate_limited': info.is_rate_limited,
                'config': {
                    'enabled': info.config.enabled,
                    'timeout': info.config.timeout,
                    'retry_count': info.config.retry_count,
                    'max_requests_per_minute': info.config.max_requests_per_minute,
                    'priority': info.config.priority
                }
            }
        
        return stats
    
    def reset_translator_stats(self, translator_name: Optional[str] = None):
        """
        重置翻译器统计信息
        
        Args:
            translator_name: 翻译器名称，None表示重置所有翻译器
        """
        if translator_name:
            if translator_name in self.translators:
                info = self.translators[translator_name]
                info.error_count = 0
                info.success_count = 0
                info.total_requests = 0
                info.avg_response_time = 0.0
                info.last_error_time = None
                info.status = TranslatorStatus.AVAILABLE
        else:
            for info in self.translators.values():
                info.error_count = 0
                info.success_count = 0
                info.total_requests = 0
                info.avg_response_time = 0.0
                info.last_error_time = None
                info.status = TranslatorStatus.AVAILABLE
        
        self.reporter.info(f"已重置翻译器统计信息: {translator_name or '所有翻译器'}")