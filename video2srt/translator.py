# -*- coding: utf-8 -*-
"""
翻译器模块 - 优化版本

提供多种翻译服务的统一接口，支持：
- Google 翻译
- OpenAI GPT 翻译
- 百度翻译
- 腾讯翻译
- 阿里云翻译
- 离线翻译（googletrans, deep_translator）

优化特性：
- 连接池和会话复用
- 智能缓存系统
- 统一错误处理
- 类型安全
"""

import os
from typing import List, Dict, Any, Optional, Protocol, Union
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import json
from functools import lru_cache

from .config_manager import config_manager
from .models import Segment, TranslationResult


# 自定义异常类
class TranslationError(Exception):
    """翻译相关的基础异常"""
    pass


class NetworkError(TranslationError):
    """网络请求相关异常"""
    pass


class APIError(TranslationError):
    """API 调用相关异常"""
    pass


class TranslationProvider(Protocol):
    """翻译提供者协议"""
    def translate_text(self, text: str, target_language: str) -> str:
        """翻译单个文本"""
        ...


class Translator:
    """翻译器基类 - 优化版本，提供统一的翻译接口"""

    def translate_text(self, text: str, target_language: str) -> str:
        """翻译单个文本 - 子类必须实现"""
        raise NotImplementedError("子类必须实现 translate_text 方法")

    def translate_segments(self, segments: List[Segment], 
                          target_language: str, source_language: str = "auto") -> TranslationResult:
        """
        翻译字幕段落列表
        
        Args:
            segments: 字幕段落列表
            target_language: 目标语言
            source_language: 源语言，默认为 "auto"
            
        Returns:
            翻译结果对象
        """
        if not segments:
             return TranslationResult(segments=[], source_language=source_language, target_language=target_language, translator_name=self.__class__.__name__)

        # 从配置获取翻译模式（尊重配置，默认逐段翻译）
        translation_mode = config_manager.get('translation.mode', 'per_segment')

        if translation_mode == 'per_segment':
            return self._translate_segments_per_segment(segments, target_language, source_language)
        elif translation_mode == 'block':
            return self._translate_segments_block_mode(segments, target_language, source_language)
        else:
            raise TranslationError(f"不支持的翻译模式: {translation_mode}")

    def _translate_segments_per_segment(self, segments: List[Segment], target_language: str, source_language: str) -> TranslationResult:
        """逐段翻译模式 - 优化版本"""
        translated_segments: List[Segment] = []
        
        # 获取上下文配置（尊重配置，限制窗口大小以保持稳定）
        context_enabled = config_manager.get('translation.context_enabled', True)
        # 将窗口限制在合理范围，避免过大窗口影响分段稳定性
        context_window = config_manager.get('translation.context_window', 2)
        if not isinstance(context_window, int):
            context_window = 2
        context_window = max(0, min(context_window, 5))
        
        for i, segment in enumerate(segments):
            try:
                if context_enabled and hasattr(self, '_translate_with_context'):
                    # 构建上下文
                    context_text = self._build_context_text(segments, i)
                    translated_text = self._translate_with_context(
                        context_text, segment.text, target_language, 
                        segment.start, segment.end
                    )
                else:
                    # 普通翻译
                    if not segment.text.strip():
                        # 跳过空文本段落
                        translated_segments.append(segment)
                        continue
                        
                    translated_text = self.translate_text(segment.text, target_language)
                
                # 确保翻译结果不为空
                if not translated_text.strip():
                    translated_text = segment.text  # 使用原文作为备选
                
                translated_segment = Segment(
                    start=segment.start,
                    end=segment.end,
                    text=translated_text.strip()
                )
                translated_segments.append(translated_segment)
                
            except Exception as e:
                print(f"翻译段落失败 (索引 {i}): {e}")
                # 使用原文作为备选
                translated_segments.append(segment)
        
        return TranslationResult(
             segments=translated_segments,
             source_language=source_language,
             target_language=target_language,
             translator_name=self.__class__.__name__
         )

    def _translate_segments_block_mode(self, segments: List[Segment], target_language: str, source_language: str) -> TranslationResult:
        """块翻译模式 - 优化版本（保持时间轴，按块翻译并智能切分）"""
        # 获取块翻译配置
        max_block_chars = config_manager.get('translation.max_block_chars', 2000)
        max_gap_seconds = config_manager.get('translation.max_gap_seconds', 5.0)
        structured_prompt = config_manager.get('translation.structured_prompt', True)
        
        # 构建文本块
        blocks = self._build_blocks(segments, max_block_chars, max_gap_seconds)
        
        translated_segments: List[Segment] = []
        
        for block in blocks:
            try:
                # 提取原始文本
                original_texts = [segments[i].text for i in block['segment_indices']]
                
                # 过滤空文本
                non_empty_texts = [text for text in original_texts if text.strip()]
                if not non_empty_texts:
                    # 如果块中所有文本都为空，跳过翻译
                    for segment_index in block['segment_indices']:
                        translated_segments.append(segments[segment_index])
                    continue
                
                # 如果支持结构化提示并且是 OpenAI 翻译器，则使用时间轴结构化翻译，确保返回附带时间轴标识
                if structured_prompt and isinstance(self, OpenAITranslator):
                    items = []
                    for seg_idx in block['segment_indices']:
                        seg = segments[seg_idx]
                        items.append({
                            "id": seg_idx,
                            "start": self._format_timestamp(seg.start),
                            "end": self._format_timestamp(seg.end),
                            "text": seg.text
                        })

                    try:
                        mapped = self.translate_block_with_structure(items, target_language)
                        # mapped: Dict[id, {start, end, text_translated}]
                        use_ai_ts = config_manager.get('translation.use_ai_timestamps', True)
                        for seg_idx in block['segment_indices']:
                            original_segment = segments[seg_idx]
                            entry = mapped.get(seg_idx)
                            final_text = original_segment.text
                            if entry and isinstance(entry, dict):
                                t = entry.get("text_translated", "")
                                if t and t.strip():
                                    final_text = t.strip()
                            # 根据配置决定是否使用 AI 返回的时间戳
                            if entry and use_ai_ts:
                                ai_start = self._parse_timestamp_to_seconds(entry.get("start", ""))
                                ai_end = self._parse_timestamp_to_seconds(entry.get("end", ""))
                                start_val = ai_start if ai_start is not None else original_segment.start
                                end_val = ai_end if ai_end is not None else original_segment.end
                            else:
                                start_val = original_segment.start
                                end_val = original_segment.end
                            translated_segments.append(Segment(
                                start=start_val,
                                end=end_val,
                                text=final_text
                            ))
                        continue
                    except Exception as se:
                        # 结构化翻译失败则回退到普通块翻译
                        print(f"结构化块翻译失败，回退比例切分：{se}")

                # 普通块翻译：合并文本后整体翻译，再按比例与标点优先切分
                combined_text = '\n'.join(original_texts)

                translated_text = self.translate_text(combined_text, target_language)

                if not translated_text.strip():
                    for segment_index in block['segment_indices']:
                        translated_segments.append(segments[segment_index])
                    continue

                split_translations = self._split_translated_text_by_ratio(translated_text, original_texts)

                for i, translation in enumerate(split_translations):
                    segment_index = block['segment_indices'][i]
                    original_segment = segments[segment_index]
                    final_text = translation.strip() if translation.strip() else original_segment.text
                    translated_segments.append(Segment(
                        start=original_segment.start,
                        end=original_segment.end,
                        text=final_text
                    ))
                    
            except Exception as e:
                print(f"翻译块失败: {e}")
                # 使用原文作为备选
                for segment_index in block['segment_indices']:
                    translated_segments.append(segments[segment_index])
        
        return TranslationResult(
             segments=translated_segments,
             source_language=source_language,
             target_language=target_language,
             translator_name=self.__class__.__name__
         )

    def translate_texts(self, texts: List[str], target_language: str) -> List[str]:
        """
        批量翻译文本 - 默认实现，子类可以重写以提供更高效的批量翻译
        """
        return [self.translate_text(text, target_language) for text in texts]

    def _build_blocks(self, segments: List[Segment], max_block_chars: int, max_gap_seconds: float) -> List[Dict[str, Any]]:
        """构建翻译块 - 优化版本"""
        blocks: List[Dict[str, Any]] = []
        current_block: Dict[str, Any] = {
            'segment_indices': [],
            'total_chars': 0,
            'start_time': 0,
            'end_time': 0
        }
        
        for i, segment in enumerate(segments):
            segment_chars = len(segment.text)
            
            # 检查是否应该开始新块
            should_start_new_block = False
            
            if current_block['segment_indices']:
                # 检查字符数限制
                if current_block['total_chars'] + segment_chars > max_block_chars:
                    should_start_new_block = True
                
                # 检查时间间隔
                last_segment_index = current_block['segment_indices'][-1]
                last_segment = segments[last_segment_index]
                time_gap = segment.start - last_segment.end
                
                if time_gap > max_gap_seconds:
                    should_start_new_block = True
            
            if should_start_new_block and current_block['segment_indices']:
                blocks.append(current_block)
                current_block = {
                    'segment_indices': [],
                    'total_chars': 0,
                    'start_time': segment.start,
                    'end_time': segment.end
                }
            
            # 添加当前段落到块中
            current_block['segment_indices'].append(i)
            current_block['total_chars'] += segment_chars
            
            if not current_block['segment_indices'] or i == 0:
                current_block['start_time'] = segment.start
            current_block['end_time'] = segment.end
        
        # 添加最后一个块
        if current_block['segment_indices']:
            blocks.append(current_block)
        
        return blocks

    def _split_translated_text_by_ratio(self, translated_text: str, original_texts: List[str]) -> List[str]:
        """按原文长度比例分割翻译文本 - 智能分割版本"""
        if not original_texts:
            return []
        
        if len(original_texts) == 1:
            return [translated_text.strip()]
        
        # 计算每个原文的长度比例
        total_original_chars = sum(len(text) for text in original_texts)
        if total_original_chars == 0:
            # 如果原文都是空的，不要重复填充整段文本，保持一处文本，其余为空
            cleaned = translated_text.strip()
            if not cleaned:
                return [""] * len(original_texts)
            return [cleaned] + [""] * (len(original_texts) - 1)
        
        ratios = [len(text) / total_original_chars for text in original_texts]
        
        # 定义句读标点（中文和英文）
        sentence_endings = {'。', '！', '？', '；', '.', '!', '?', ';', '——', '…'}
        
        # 按比例分割翻译文本，但优先在句读标点处分割
        translated_chars = len(translated_text)
        split_positions = []
        current_pos = 0
        
        for i, ratio in enumerate(ratios[:-1]):  # 最后一个不需要计算位置
            target_pos = current_pos + int(translated_chars * ratio)
            
            # 在目标位置附近寻找最佳分割点
            best_split_pos = self._find_best_split_position(
                translated_text, current_pos, target_pos, sentence_endings
            )
            
            # 保证切分位置严格前进，避免产生零长度片段
            if best_split_pos <= current_pos:
                if current_pos < translated_chars:
                    best_split_pos = min(translated_chars, current_pos + 1)
                else:
                    best_split_pos = current_pos
            
            split_positions.append(best_split_pos)
            current_pos = best_split_pos
        
        # 分割文本
        result = []
        start_pos = 0
        
        for split_pos in split_positions:
            segment_text = translated_text[start_pos:split_pos].strip()
            # 避免产生过短或纯标点的片段
            if len(segment_text) <= 2 and segment_text in sentence_endings:
                # 如果是纯标点，合并到前一个片段
                if result:
                    result[-1] = result[-1] + segment_text
                    segment_text = ""
            if segment_text:
                result.append(segment_text)
            start_pos = split_pos
        
        # 添加最后一部分
        last_segment = translated_text[start_pos:].strip()
        if last_segment:
            result.append(last_segment)
        
        # 确保结果数量与原文数量一致
        while len(result) < len(original_texts):
            result.append("")
        while len(result) > len(original_texts):
            # 合并多余的片段到最后一个
            if len(result) > 1:
                result[-2] = result[-2] + " " + result[-1]
                result.pop()
            else:
                break

        # 最终重平衡：避免出现空片段，尽量从邻近片段借用文本
        def _borrow_head(text: str, max_chars: int = 30) -> str:
            if not text:
                return ""
            # 到首个空格或句读的截断
            for idx, ch in enumerate(text[:max_chars]):
                if ch in sentence_endings or ch.isspace():
                    return text[:idx+1].strip()
            return text[:max_chars].strip()

        def _borrow_tail(text: str, max_chars: int = 30) -> str:
            if not text:
                return ""
            # 从尾部到首个空格或句读的截断
            tail = text[-max_chars:]
            for i in range(len(tail)-1, -1, -1):
                ch = tail[i]
                if ch in sentence_endings or ch.isspace():
                    return tail[i:].strip()
            return tail.strip()

        for i in range(len(result)):
            if not result[i].strip():
                # 优先从后面借
                borrowed = ""
                for j in range(i+1, len(result)):
                    if result[j].strip():
                        piece = _borrow_head(result[j], 30)
                        if piece:
                            borrowed = piece
                            # 从后片段中移除借出的文本
                            result[j] = result[j][len(piece):].lstrip()
                            break
                # 如果后面没借到，从前面借
                if not borrowed and i > 0 and result[i-1].strip():
                    piece = _borrow_tail(result[i-1], 30)
                    if piece:
                        borrowed = piece
                        result[i-1] = result[i-1][:-len(piece)].rstrip()
                # 如果仍为空，填充省略符，避免空行
                result[i] = borrowed if borrowed else "…"
        
        return result
    
    def _find_best_split_position(self, text: str, start_pos: int, target_pos: int, sentence_endings: set) -> int:
        """在目标位置附近寻找最佳分割点"""
        if target_pos >= len(text):
            return len(text)
        
        # 搜索范围：目标位置前后20个字符
        search_range = 20
        search_start = max(start_pos, target_pos - search_range)
        search_end = min(len(text), target_pos + search_range)
        
        # 优先寻找句读标点
        for i in range(target_pos, search_end):
            if i < len(text) and text[i] in sentence_endings:
                return i + 1  # 在标点后分割
        
        for i in range(target_pos - 1, search_start - 1, -1):
            if i >= 0 and text[i] in sentence_endings:
                return i + 1  # 在标点后分割
        
        # 如果没有找到句读标点，寻找空白字符
        for i in range(target_pos, search_end):
            if i < len(text) and text[i].isspace():
                return i + 1  # 在空白后分割
        
        for i in range(target_pos - 1, search_start - 1, -1):
            if i >= 0 and text[i].isspace():
                return i + 1  # 在空白后分割
        
        # 最后回退到原始目标位置
        return target_pos

    def _build_context_text(self, context_segments: List[Segment], 
                           current_index: int) -> str:
        """构建上下文文本 - 优化版本"""
        context_window = config_manager.get('translation.context_window', 2)
        
        # 获取上下文范围
        start_idx = max(0, current_index - context_window)
        end_idx = min(len(context_segments), current_index + context_window + 1)
        
        context_lines = []
        for i in range(start_idx, end_idx):
            segment = context_segments[i]
            timestamp = self._format_timestamp(segment.start)
            
            if i == current_index:
                context_lines.append(f"[CURRENT] {timestamp}: {segment.text}")
            else:
                context_lines.append(f"{timestamp}: {segment.text}")
        
        return '\n'.join(context_lines)

    def _format_timestamp(self, seconds: float) -> str:
        """格式化时间戳 - 优化版本"""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"

    def _parse_timestamp_to_seconds(self, ts: str) -> Optional[float]:
        """将时间戳字符串解析为秒，支持 HH:MM:SS、HH:MM:SS.mmm、HH:MM:SS,mmm 格式"""
        try:
            t = ts.strip()
            if not t:
                return None
            parts = t.split(':')
            if len(parts) != 3:
                return None
            h = int(parts[0])
            m = int(parts[1])
            s_part = parts[2]
            ms = 0
            if ',' in s_part:
                s_str, ms_str = s_part.split(',', 1)
                s = int(s_str)
                ms = int(ms_str[:3].ljust(3, '0'))
            elif '.' in s_part:
                s_str, ms_str = s_part.split('.', 1)
                s = int(s_str)
                ms = int(ms_str[:3].ljust(3, '0'))
            else:
                s = int(s_part)
            return h * 3600 + m * 60 + s + ms / 1000.0
        except Exception:
            return None

    def _translate_with_context(self, context_text: str, current_text: str, 
                              target_language: str, start_time: float, end_time: float) -> str:
        """基于上下文翻译 - 默认实现，子类可以重写"""
        # 默认实现：忽略上下文，直接翻译
        return self.translate_text(current_text, target_language)


class GoogleTranslator(Translator):
    """Google 翻译器 - 优化版本，支持连接池和会话复用"""
    
    def __init__(self):
        self.base_url = "https://translate.googleapis.com/translate_a/single"
        # 从配置文件加载设置
        self.config = config_manager.get_translator_config('google')
        self.timeout = self.config.get('timeout', 15)
        self.retry_count = self.config.get('retry_count', 3)
        
        # 创建持久化会话，配置连接池和重试策略
        self._session = self._create_session()
    
    def _create_session(self) -> requests.Session:
        """创建配置好的会话对象"""
        session = requests.Session()
        
        # 配置重试策略
        retry_strategy = Retry(
            total=self.retry_count,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET", "POST"]
        )
        
        # 配置连接池适配器
        adapter = HTTPAdapter(
            pool_connections=10,  # 连接池大小
            pool_maxsize=20,      # 最大连接数
            max_retries=retry_strategy
        )
        
        session.mount("https://", adapter)
        session.mount("http://", adapter)
        
        # 设置默认请求头
        session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        
        return session
    
    def __del__(self):
        """清理资源"""
        if hasattr(self, '_session'):
            self._session.close()
    
    def _translate_with_context(self, context_text: str, current_text: str, 
                              target_language: str, start_time: float, end_time: float) -> str:
        """基于上下文翻译当前文本"""
        # 对于Google翻译，上下文信息主要用于日志记录，实际翻译还是使用当前文本
        return self.translate_text(current_text, target_language)
    
    def translate_text(self, text: str, target_language: str) -> str:
        """使用 Google 翻译 API - 优化版本"""
        if not text or not text.strip():
            return text
            
        try:
            params = {
                "client": "gtx",
                "sl": "auto",  # 自动检测源语言
                "tl": target_language,
                "dt": "t",
                "q": text
            }
            
            # 使用持久化会话发送请求
            response = self._session.get(
                self.base_url, 
                params=params, 
                timeout=self.timeout
            )
            response.raise_for_status()
            
            result = response.json()
            if result and len(result) > 0 and len(result[0]) > 0:
                translated_parts = [item[0] for item in result[0] if item[0]]
                translated_text = "".join(translated_parts)
                if translated_text and translated_text.strip():
                    return translated_text.strip()
                else:
                    raise APIError(f"Google 翻译返回空结果: {text}")
            else:
                raise APIError(f"Google 翻译返回无效结果: {text}")
                
        except requests.exceptions.SSLError as e:
            raise NetworkError(f"SSL 证书验证失败: {e}")
        except requests.exceptions.Timeout as e:
            raise NetworkError(f"请求超时: {e}")
        except requests.exceptions.ConnectionError as e:
            raise NetworkError(f"连接错误: {e}")
        except requests.exceptions.RequestException as e:
            raise NetworkError(f"网络请求失败: {e}")
        except json.JSONDecodeError as e:
            raise APIError(f"响应解析失败: {e}")
        except Exception as e:
            raise TranslationError(f"Google 翻译失败: {e}")
    
    def translate_texts(self, texts: List[str], target_language: str) -> List[str]:
        """批量翻译 - 复用会话连接"""
        results = []
        for text in texts:
            try:
                result = self.translate_text(text, target_language)
                results.append(result)
            except TranslationError:
                # 如果单个翻译失败，使用原文
                results.append(text)
        return results


class OpenAITranslator(Translator):
    """OpenAI GPT 翻译器 - 优化版本，支持客户端复用和智能缓存"""
    
    def __init__(self, api_key: Optional[str] = None):
        # 优先使用传入的 API Key，然后从配置文件，最后从环境变量
        self.api_key = api_key or config_manager.get_openai_api_key() or os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("需要设置 OpenAI API Key")
        
        # 从配置文件加载设置
        self.config = config_manager.get_openai_config()
        self.base_url = self.config.get('base_url', 'https://api.openai.com/v1')
        self.model = self.config.get('model', 'gpt-3.5-turbo')
        self.max_tokens = self.config.get('max_tokens', 4000)
        self.temperature = self.config.get('temperature', 0.3)
        
        # 缓存配置
        self.cache_enabled = bool(config_manager.get('translation.cache_enabled', True))
        cache_size = config_manager.get('translation.cache_size', 1000)
        
        # 使用 LRU 缓存替代简单字典
        if self.cache_enabled:
            self._cache = self._create_cache(cache_size)
        
        # 创建持久化客户端
        self._client = None
        self._language_names = {
            "en": "英语", "zh": "中文", "ja": "日语", "ko": "韩语",
            "fr": "法语", "de": "德语", "es": "西班牙语", "ru": "俄语"
        }
    
    @lru_cache(maxsize=1)
    def _create_cache(self, size: int):
        """创建缓存对象 - 使用 LRU 缓存装饰器"""
        # 这里实际上我们会在实例级别管理缓存
        return {}
    
    def _get_client(self):
        """获取或创建 OpenAI 客户端"""
        if self._client is None:
            try:
                import openai
                self._client = openai.OpenAI(
                    api_key=self.api_key,
                    base_url=self.base_url
                )
            except ImportError:
                raise TranslationError("需要安装 openai 库: pip install openai")
        return self._client
    
    def _get_cache_key(self, text: str, target_language: str) -> str:
        """生成缓存键"""
        return f"{target_language}::{hash(text)}"
    
    def _translate_with_context(self, context_text: str, current_text: str, 
                              target_language: str, start_time: float, end_time: float) -> str:
        """基于上下文翻译当前文本"""
        try:
            client = self._get_client()
            target_lang_name = self._language_names.get(target_language, target_language)
            
            # 构建带上下文的翻译提示
            prompt = f"""你是一个专业的字幕翻译助手。请将以下字幕文本翻译成{target_lang_name}，保持字幕的简洁性和准确性。

上下文信息（包含时间戳）：
{context_text}

请只翻译标记为 [CURRENT] 的文本，返回翻译结果。要求：
1. 保持字幕的简洁性，适合屏幕显示
2. 保持原文的语气和风格
3. 只返回翻译结果，不要添加任何解释
4. 确保翻译准确且符合目标语言习惯

翻译结果："""
            
            response = client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": f"你是一个专业的字幕翻译助手，专门将视频字幕翻译成{target_lang_name}。"
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                max_tokens=self.max_tokens,
                temperature=self.temperature
            )
            
            translated_text = response.choices[0].message.content.strip()
            
            # 清理翻译结果
            if translated_text:
                # 移除可能的前缀
                prefixes_to_remove = ["翻译结果：", "翻译：", "译文：", "Translation:", "Translated:"]
                for prefix in prefixes_to_remove:
                    if translated_text.startswith(prefix):
                        translated_text = translated_text[len(prefix):].strip()
                
                return translated_text
            else:
                raise APIError(f"OpenAI 翻译返回空结果: {current_text}")
                
        except Exception as e:
            if isinstance(e, TranslationError):
                raise
            raise TranslationError(f"OpenAI 上下文翻译失败: {e}")
    
    def translate_text(self, text: str, target_language: str) -> str:
        """使用 OpenAI GPT 进行翻译 - 优化版本"""
        if not text or not text.strip():
            return text
            
        # 检查缓存
        if self.cache_enabled:
            cache_key = self._get_cache_key(text, target_language)
            if cache_key in self._cache:
                return self._cache[cache_key]
        
        try:
            client = self._get_client()
            target_lang_name = self._language_names.get(target_language, target_language)
            
            response = client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": f"你是一个专业的翻译助手。请将以下文本翻译成{target_lang_name}，保持原文的语气和风格，只返回翻译结果，不要添加任何解释。"
                    },
                    {
                        "role": "user",
                        "content": text
                    }
                ],
                max_tokens=self.max_tokens,
                temperature=self.temperature
            )
            
            translated_text = response.choices[0].message.content.strip()
            
            # 缓存结果
            if self.cache_enabled and translated_text:
                cache_key = self._get_cache_key(text, target_language)
                self._cache[cache_key] = translated_text
                
                # 简单的缓存大小控制
                if len(self._cache) > 1000:
                    # 移除最旧的一半缓存项
                    keys_to_remove = list(self._cache.keys())[:500]
                    for key in keys_to_remove:
                        del self._cache[key]
            
            return translated_text
            
        except Exception as e:
            if "openai" in str(e).lower():
                raise APIError(f"OpenAI API 错误: {e}")
            raise TranslationError(f"OpenAI 翻译失败: {e}")

    def translate_block_with_structure(self, items: List[Dict[str, Any]], target_language: str) -> Dict[int, Dict[str, str]]:
        """
        结构化块翻译：向模型发送包含时间轴的 JSON，并要求返回保持 id/start/end 的 JSON 字段。
        返回字典：{ id: {"start": str, "end": str, "text_translated": str} }
        """
        if not items:
            return {}
        client = self._get_client()
        target_lang_name = self._language_names.get(target_language, target_language)

        # 构建 JSON 提示
        payload = {
            "segments": [
                {
                    "id": int(it.get("id")),
                    "start": str(it.get("start", "")),
                    "end": str(it.get("end", "")),
                    "text": str(it.get("text", ""))
                } for it in items
            ]
        }

        use_ai_ts = config_manager.get('translation.use_ai_timestamps', True)
        if use_ai_ts:
            system_prompt = (
                f"你是字幕翻译助手。请将输入 JSON 中的每个 segments[i].text 翻译成{target_lang_name}。\n"
                "严格返回 JSON：对每个输入段保留 id，并新增/填写 start、end 与 text_translated。\n"
                "注意：\n"
                "- 段的数量与顺序必须与输入一致；\n"
                "- 可以根据语义/语音边界微调 start 与 end（格式 HH:MM:SS 或 HH:MM:SS.mmm）；\n"
                "- 不要生成额外解释或文本；\n"
                "- 返回的 JSON 顶层必须是 {\"segments\": [...]}。"
            )
        else:
            system_prompt = (
                f"你是字幕翻译助手。请将输入 JSON 中的每个 segments[i].text 翻译成{target_lang_name}。\n"
                "严格返回 JSON，对每个输入段保留 id、start、end，并新增字段 text_translated。\n"
                "注意：\n"
                "- 不要改变段的数量与顺序；\n"
                "- start、end 必须与输入完全一致；\n"
                "- 不要生成额外解释或文本；\n"
                "- 返回的 JSON 顶层必须是 {\"segments\": [...]}。"
            )

        user_content = (
            "请翻译以下 JSON，并仅返回规定格式的 JSON：\n" + json.dumps(payload, ensure_ascii=False)
        )

        try:
            resp = client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_content}
                ],
                max_tokens=self.max_tokens,
                temperature=self.temperature
            )
            content = resp.choices[0].message.content.strip()

            # 尝试解析 JSON；有些模型可能返回被包裹在代码块中的 JSON，需要剥离
            def _extract_json(text: str) -> str:
                t = text.strip()
                if t.startswith("```"):
                    # 可能是 ```json\n...\n```
                    t = t.strip('`')
                    # 尝试寻找第一个 '{' 到最后一个 '}'
                start = t.find('{')
                end = t.rfind('}')
                if start != -1 and end != -1 and end > start:
                    return t[start:end+1]
                return t

            json_text = _extract_json(content)
            parsed = json.loads(json_text)
            segs = parsed.get("segments", [])

            result: Dict[int, Dict[str, str]] = {}
            for seg in segs:
                sid = int(seg.get("id"))
                start = str(seg.get("start", ""))
                end = str(seg.get("end", ""))
                txt = str(seg.get("text_translated", "")).strip()
                result[sid] = {"start": start, "end": end, "text_translated": txt}

            return result
        except Exception as e:
            # 解析或 API 失败，抛出异常以便上层回退到普通块翻译
            raise TranslationError(f"OpenAI 结构化块翻译失败: {e}")

    def translate_texts(self, texts: List[str], target_language: str) -> List[str]:
        """OpenAI 批量翻译实现 - 优化版本"""
        client = self._get_client()
        target_lang_name = self._language_names.get(target_language, target_language)

        results: List[str] = []
        for text in texts:
            if not text or not text.strip():
                results.append(text)
                continue
                
            # 检查缓存
            if self.cache_enabled:
                cache_key = self._get_cache_key(text, target_language)
                if cache_key in self._cache:
                    results.append(self._cache[cache_key])
                    continue

            try:
                resp = client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {
                            "role": "system",
                            "content": f"你是一个专业的翻译助手。请将以下文本翻译成{target_lang_name}，保持原文语气和风格，只返回翻译结果，不要任何解释。"
                        },
                        {
                            "role": "user",
                            "content": text
                        }
                    ],
                    max_tokens=self.max_tokens,
                    temperature=self.temperature
                )
                translated = resp.choices[0].message.content.strip()
                
                # 缓存结果
                if self.cache_enabled and translated:
                    cache_key = self._get_cache_key(text, target_language)
                    self._cache[cache_key] = translated
                
                results.append(translated)
            except Exception as e:
                print(f"OpenAI 批量翻译失败: {e}，使用原文")
                results.append(text)

        return results


class SimpleTranslator(Translator):
    """简单翻译器 - 优化版本，支持缓存和统一错误处理"""
    
    def __init__(self):
        # 缓存配置
        self.cache_enabled = bool(config_manager.get('translation.cache_enabled', True))
        if self.cache_enabled:
            self._cache = {}
    
    def _get_cache_key(self, text: str, target_language: str) -> str:
        """生成缓存键"""
        return f"{target_language}::{hash(text)}"
    
    def translate_text(self, text: str, target_language: str) -> str:
        """简单翻译实现 - 直接返回原文"""
        if not text or not text.strip():
            return text
            
        # 检查缓存
        if self.cache_enabled:
            cache_key = self._get_cache_key(text, target_language)
            if cache_key in self._cache:
                return self._cache[cache_key]
        
        # 简单翻译：直接返回原文
        result = text
        
        # 缓存结果
        if self.cache_enabled:
            cache_key = self._get_cache_key(text, target_language)
            self._cache[cache_key] = result
        
        return result


class OfflineTranslator(Translator):
    """离线翻译器 - 优化版本，支持 googletrans 和 deep_translator"""
    
    def __init__(self, provider: str = "googletrans"):
        self.provider = provider
        self._translator = None
        
        # 缓存配置
        self.cache_enabled = bool(config_manager.get('translation.cache_enabled', True))
        if self.cache_enabled:
            self._cache = {}
        
        # 初始化翻译器
        self._init_translator()
    
    def _init_translator(self):
        """初始化翻译器实例"""
        try:
            if self.provider == "googletrans":
                from googletrans import Translator as GoogleTranslator
                self._translator = GoogleTranslator()
            elif self.provider == "deep_translator":
                # deep_translator 需要在使用时动态导入
                pass
            else:
                raise ValueError(f"不支持的离线翻译器: {self.provider}")
        except ImportError as e:
            raise TranslationError(f"无法导入 {self.provider}: {e}")
    
    def _get_cache_key(self, text: str, target_language: str) -> str:
        """生成缓存键"""
        return f"{self.provider}::{target_language}::{hash(text)}"
    
    def translate_text(self, text: str, target_language: str) -> str:
        """离线翻译实现 - 优化版本"""
        if not text or not text.strip():
            return text
            
        # 检查缓存
        if self.cache_enabled:
            cache_key = self._get_cache_key(text, target_language)
            if cache_key in self._cache:
                return self._cache[cache_key]
        
        try:
            if self.provider == "googletrans":
                result = self._translator.translate(text, dest=target_language)
                translated_text = result.text
            elif self.provider == "deep_translator":
                from deep_translator import GoogleTranslator
                translator = GoogleTranslator(source='auto', target=target_language)
                translated_text = translator.translate(text)
            else:
                raise TranslationError(f"不支持的翻译器: {self.provider}")
            
            # 缓存结果
            if self.cache_enabled and translated_text:
                cache_key = self._get_cache_key(text, target_language)
                self._cache[cache_key] = translated_text
                
                # 简单的缓存大小控制
                if len(self._cache) > 500:
                    keys_to_remove = list(self._cache.keys())[:250]
                    for key in keys_to_remove:
                        del self._cache[key]
            
            return translated_text
            
        except ImportError as e:
            raise TranslationError(f"缺少依赖库 {self.provider}: {e}")
        except Exception as e:
            if "quota" in str(e).lower() or "limit" in str(e).lower():
                raise APIError(f"{self.provider} 配额限制: {e}")
            raise TranslationError(f"{self.provider} 翻译失败: {e}")


class BaiduTranslator(Translator):
    """百度翻译器 - 优化版本，支持连接池和缓存"""
    
    def __init__(self):
        self.config = config_manager.get_translator_config('baidu')
        self.app_id = self.config.get('app_id', '')
        self.secret_key = self.config.get('secret_key', '')
        
        if not self.app_id or not self.secret_key:
            raise TranslationError("需要设置百度翻译的 app_id 和 secret_key")
        
        # 缓存配置
        self.cache_enabled = bool(config_manager.get('translation.cache_enabled', True))
        if self.cache_enabled:
            self._cache = {}
        
        # 创建持久化会话
        self._session = self._create_session()
    
    def _create_session(self) -> requests.Session:
        """创建带连接池的会话"""
        session = requests.Session()
        
        # 配置重试策略
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
        )
        
        # 配置连接池
        adapter = HTTPAdapter(
            pool_connections=10,
            pool_maxsize=20,
            max_retries=retry_strategy
        )
        
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        
        return session
    
    def _get_cache_key(self, text: str, target_language: str) -> str:
        """生成缓存键"""
        return f"baidu::{target_language}::{hash(text)}"
    
    def translate_text(self, text: str, target_language: str) -> str:
        """使用百度翻译 API - 优化版本"""
        if not text or not text.strip():
            return text
            
        # 检查缓存
        if self.cache_enabled:
            cache_key = self._get_cache_key(text, target_language)
            if cache_key in self._cache:
                return self._cache[cache_key]
        
        try:
            import hashlib
            import random
            
            # 生成签名
            salt = str(random.randint(32768, 65536))
            sign_str = self.app_id + text + salt + self.secret_key
            sign = hashlib.md5(sign_str.encode('utf-8')).hexdigest()
            
            # 构建请求参数
            params = {
                'q': text,
                'from': 'auto',
                'to': target_language,
                'appid': self.app_id,
                'salt': salt,
                'sign': sign
            }
            
            response = self._session.get(
                'https://fanyi-api.baidu.com/api/trans/vip/translate',
                params=params,
                timeout=10
            )
            response.raise_for_status()
            
            result = response.json()
            if 'trans_result' in result and result['trans_result']:
                translated_text = result['trans_result'][0]['dst']
                
                # 缓存结果
                if self.cache_enabled and translated_text:
                    cache_key = self._get_cache_key(text, target_language)
                    self._cache[cache_key] = translated_text
                    
                    # 简单的缓存大小控制
                    if len(self._cache) > 500:
                        keys_to_remove = list(self._cache.keys())[:250]
                        for key in keys_to_remove:
                            del self._cache[key]
                
                return translated_text
            elif 'error_code' in result:
                raise APIError(f"百度翻译 API 错误: {result.get('error_msg', '未知错误')}")
            else:
                raise APIError("百度翻译返回格式错误")
                
        except requests.RequestException as e:
            raise NetworkError(f"百度翻译网络请求失败: {e}")
        except Exception as e:
            if isinstance(e, TranslationError):
                raise
            raise TranslationError(f"百度翻译失败: {e}")


class TencentTranslator(Translator):
    """腾讯翻译器 - 优化版本，支持缓存"""
    
    def __init__(self):
        self.config = config_manager.get_translator_config('tencent')
        self.secret_id = self.config.get('secret_id', '')
        self.secret_key = self.config.get('secret_key', '')
        
        if not self.secret_id or not self.secret_key:
            raise TranslationError("需要设置腾讯翻译的 secret_id 和 secret_key")
        
        # 缓存配置
        self.cache_enabled = bool(config_manager.get('translation.cache_enabled', True))
        if self.cache_enabled:
            self._cache = {}
    
    def _get_cache_key(self, text: str, target_language: str) -> str:
        """生成缓存键"""
        return f"tencent::{target_language}::{hash(text)}"
    
    def translate_text(self, text: str, target_language: str) -> str:
        """使用腾讯翻译 API - 优化版本"""
        if not text or not text.strip():
            return text
            
        # 检查缓存
        if self.cache_enabled:
            cache_key = self._get_cache_key(text, target_language)
            if cache_key in self._cache:
                return self._cache[cache_key]
        
        try:
            # TODO: 实现腾讯云完整的签名算法
            # 这里提供一个占位符实现
            print("警告: 腾讯翻译功能需要实现完整的签名算法")
            
            # 缓存结果（即使是占位符）
            if self.cache_enabled:
                cache_key = self._get_cache_key(text, target_language)
                self._cache[cache_key] = text
            
            return text
            
        except Exception as e:
            raise TranslationError(f"腾讯翻译失败: {e}")


class AliyunTranslator(Translator):
    """阿里云翻译器 - 优化版本，支持缓存"""
    
    def __init__(self):
        self.config = config_manager.get_translator_config('aliyun')
        self.access_key_id = self.config.get('access_key_id', '')
        self.access_key_secret = self.config.get('access_key_secret', '')
        
        if not self.access_key_id or not self.access_key_secret:
            raise TranslationError("需要设置阿里云翻译的 access_key_id 和 access_key_secret")
        
        # 缓存配置
        self.cache_enabled = bool(config_manager.get('translation.cache_enabled', True))
        if self.cache_enabled:
            self._cache = {}
    
    def _get_cache_key(self, text: str, target_language: str) -> str:
        """生成缓存键"""
        return f"aliyun::{target_language}::{hash(text)}"
    
    def translate_text(self, text: str, target_language: str) -> str:
        """使用阿里云翻译 API - 优化版本"""
        if not text or not text.strip():
            return text
            
        # 检查缓存
        if self.cache_enabled:
            cache_key = self._get_cache_key(text, target_language)
            if cache_key in self._cache:
                return self._cache[cache_key]
        
        try:
            # TODO: 实现阿里云完整的签名算法
            # 这里提供一个占位符实现
            print("警告: 阿里云翻译功能需要实现完整的签名算法")
            
            # 缓存结果（即使是占位符）
            if self.cache_enabled:
                cache_key = self._get_cache_key(text, target_language)
                self._cache[cache_key] = text
            
            return text
            
        except Exception as e:
            raise TranslationError(f"阿里云翻译失败: {e}")


def get_translator(translator_type: str = "google", **kwargs) -> Translator:
    """
    获取翻译器实例 - 优化版本，支持更好的错误处理
    
    Args:
        translator_type: 翻译器类型 (google, openai, simple, offline, baidu, tencent, aliyun)
        **kwargs: 翻译器参数
        
    Returns:
        翻译器实例
        
    Raises:
        TranslationError: 当翻译器类型不支持或初始化失败时
    """
    try:
        if translator_type == "google":
            return GoogleTranslator()
        elif translator_type == "openai":
            return OpenAITranslator(**kwargs)
        elif translator_type == "simple":
            return SimpleTranslator()
        elif translator_type == "offline":
            # 优先使用显式参数，其次使用配置，支持 auto 选择
            provider = kwargs.get('provider')
            if not provider:
                service = config_manager.get('translators.offline.service', 'googletrans')
                if service == 'auto':
                    # 自动选择：优先 googletrans，其次 deep_translator
                    try:
                        import importlib
                        importlib.import_module('googletrans')
                        provider = 'googletrans'
                    except ImportError:
                        try:
                            import importlib
                            importlib.import_module('deep_translator')
                            provider = 'deep_translator'
                        except ImportError:
                            raise TranslationError("离线翻译器自动选择失败：未安装 googletrans 或 deep_translator")
                else:
                    provider = service
            return OfflineTranslator(provider=provider)
        elif translator_type == "baidu":
            return BaiduTranslator()
        elif translator_type == "tencent":
            return TencentTranslator()
        elif translator_type == "aliyun":
            return AliyunTranslator()
        else:
            available = get_available_translators()
            raise TranslationError(f"不支持的翻译器类型: {translator_type}. 可用类型: {available}")
    except Exception as e:
        if isinstance(e, TranslationError):
            raise
        raise TranslationError(f"创建翻译器失败: {e}")


def get_available_translators() -> List[str]:
    """获取可用的翻译器列表"""
    return ["google", "openai", "simple", "offline", "baidu", "tencent", "aliyun"]


def get_default_translator() -> str:
    """获取默认翻译器"""
    return config_manager.get_default_translator()
