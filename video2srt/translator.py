"""
翻译模块
支持多种翻译服务
"""

import os
import re
import ssl
import urllib3
from typing import List, Dict, Any, Optional
import requests
import json
from .config_manager import config_manager
from .models import Segment, TranslationResult


class Translator:
    """翻译器基类"""
    
    def translate_text(self, text: str, target_language: str) -> str:
        """翻译文本"""
        raise NotImplementedError
    
    def translate_segments(self, segments: List[Segment], 
                          target_language: str, source_language: str = "auto") -> TranslationResult:
        """
        翻译分段文本，支持两种模式：
        - per_segment：逐段翻译（保留旧实现的行为）
        - block：按句/段合并为块后整体翻译，再映射回原分段（更省成本、提升上下文一致性）
        
        通过配置 translation.mode 控制，默认使用 block。
        """
        if not segments:
            return TranslationResult(
                segments=[],
                source_language=source_language,
                target_language=target_language,
                translator_name=self.__class__.__name__
            )

        mode = config_manager.get('translation.mode', 'block')
        if mode == 'per_segment':
            return self._translate_segments_per_segment(segments, target_language, source_language)
        else:
            return self._translate_segments_block_mode(segments, target_language, source_language)

    def _translate_segments_per_segment(self, segments: List[Segment], target_language: str, source_language: str) -> TranslationResult:
        """保持原有逐段+固定窗口上下文的实现"""
        translated_segments = []
        context_window = config_manager.get('translation.context_window', 10)

        for i, segment in enumerate(segments):
            start_idx = max(0, i - context_window // 2)
            end_idx = min(len(segments), i + context_window // 2 + 1)
            context_segments = segments[start_idx:end_idx]

            context_text = self._build_context_text(context_segments, i - start_idx)

            translated_text = self._translate_with_context(
                context_text,
                segment.text,
                target_language,
                segment.start,
                segment.end
            )

            translated_segments.append(Segment(
                start=segment.start,
                end=segment.end,
                text=translated_text,
                language=target_language
            ))

        return TranslationResult(
            segments=translated_segments,
            source_language=source_language,
            target_language=target_language,
            translator_name=self.__class__.__name__
        )

    def _translate_segments_block_mode(self, segments: List[Segment], target_language: str, source_language: str) -> TranslationResult:
        """按块翻译并回映射到原分段，兼顾语义与速率/成本"""
        # 构建块
        max_block_chars = int(config_manager.get('translation.max_block_chars', 600))
        max_gap_seconds = float(config_manager.get('translation.max_gap_seconds', 1.0))
        blocks = self._build_blocks(segments, max_block_chars=max_block_chars, max_gap_seconds=max_gap_seconds)

        # 翻译块（支持批量）
        block_texts = [b['text'] for b in blocks]
        translated_block_texts = self.translate_texts(block_texts, target_language)

        # 将块译文映射回原分段
        mapped_segments: List[Segment] = []
        for block, translated_text in zip(blocks, translated_block_texts):
            block_segs = block['segments']
            # 使用长度比例将译文切回各分段
            original_texts = [s.text for s in block_segs]
            splits = self._split_translated_text_by_ratio(translated_text, original_texts)

            for seg, t_text in zip(block_segs, splits):
                mapped_segments.append(Segment(
                    start=seg.start,
                    end=seg.end,
                    text=t_text,
                    language=target_language
                ))

        return TranslationResult(
            segments=mapped_segments,
            source_language=source_language,
            target_language=target_language,
            translator_name=self.__class__.__name__
        )

    def translate_texts(self, texts: List[str], target_language: str) -> List[str]:
        """默认逐条翻译的批量方法，子类可覆盖以优化成本/速率"""
        results = []
        for t in texts:
            results.append(self.translate_text(t, target_language))
        return results

    def _build_blocks(self, segments: List[Segment], max_block_chars: int, max_gap_seconds: float) -> List[Dict[str, Any]]:
        """根据标点与时间间隔将分段合并成块"""
        blocks: List[Dict[str, Any]] = []
        current_block: List[Segment] = []
        current_len = 0

        def should_end_block(prev: Optional[Segment], curr: Segment, curr_len: int) -> bool:
            if prev is None:
                return False
            # 时间间隔大于阈值时切块
            if (curr.start - prev.end) > max_gap_seconds:
                return True
            # 超过最大块长度
            if curr_len > max_block_chars:
                return True
            # 当前段末尾有强标点，优先结束块
            return bool(re.search(r"[\.\!\?。！？；;]$", prev.text.strip()))

        for seg in segments:
            prev = current_block[-1] if current_block else None
            if prev and should_end_block(prev, seg, current_len + len(seg.text)):
                # 输出当前块
                block_text = " ".join(s.text.strip() for s in current_block).strip()
                if block_text:
                    blocks.append({
                        'segments': current_block,
                        'text': block_text
                    })
                current_block = []
                current_len = 0

            current_block.append(seg)
            current_len += len(seg.text)

        # 末尾块
        if current_block:
            block_text = " ".join(s.text.strip() for s in current_block).strip()
            if block_text:
                blocks.append({
                    'segments': current_block,
                    'text': block_text
                })

        return blocks

    def _split_translated_text_by_ratio(self, translated_text: str, original_texts: List[str]) -> List[str]:
        """按照原文各段的字符占比，将块译文切分为若干段"""
        if not original_texts:
            return [translated_text]
        total = sum(max(len(t), 1) for t in original_texts)
        # 依据占比计算每段的目标长度
        target_lengths = [max(1, int(round(len(t) / total * max(len(translated_text), 1)))) for t in original_texts]
        # 由于四舍五入可能导致总长不一致，调整最后一段长度以匹配
        length_diff = len(translated_text) - sum(target_lengths)
        if target_lengths:
            target_lengths[-1] += length_diff
            if target_lengths[-1] < 1:
                target_lengths[-1] = 1

        # 按长度切分
        splits = []
        idx = 0
        for tl in target_lengths:
            splits.append(translated_text[idx: idx + tl].strip())
            idx += tl
        # 如果出现空切片，用一个短空格占位，避免完全空
        splits = [s if s else "" for s in splits]
        return splits
    
    def _build_context_text(self, context_segments: List[Segment], 
                           current_index: int) -> str:
        """构建带时间戳的上下文文本"""
        context_parts = []
        
        for j, seg in enumerate(context_segments):
            timestamp = f"[{self._format_timestamp(seg.start)}-{self._format_timestamp(seg.end)}]"
            if j == current_index:
                context_parts.append(f"{timestamp} {seg.text} [CURRENT]")
            else:
                context_parts.append(f"{timestamp} {seg.text}")
        
        return "\n".join(context_parts)
    
    def _format_timestamp(self, seconds: float) -> str:
        """格式化时间戳"""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        millisecs = int((seconds % 1) * 1000)
        return f"{hours:02d}:{minutes:02d}:{secs:02d},{millisecs:03d}"
    
    def _translate_with_context(self, context_text: str, current_text: str, 
                              target_language: str, start_time: float, end_time: float) -> str:
        """基于上下文翻译当前文本"""
        # 默认实现：直接翻译当前文本
        return self.translate_text(current_text, target_language)


class GoogleTranslator(Translator):
    """Google 翻译器"""
    
    def __init__(self):
        self.base_url = "https://translate.googleapis.com/translate_a/single"
        # 从配置文件加载设置
        self.config = config_manager.get_translator_config('google')
        self.timeout = self.config.get('timeout', 15)
        self.retry_count = self.config.get('retry_count', 3)
    
    def _translate_with_context(self, context_text: str, current_text: str, 
                              target_language: str, start_time: float, end_time: float) -> str:
        """基于上下文翻译当前文本"""
        try:
            # 构建带上下文的翻译请求
            prompt = f"""请翻译以下字幕文本，保持字幕的简洁性和准确性。上下文信息仅供参考：

上下文：
{context_text}

请只翻译标记为 [CURRENT] 的文本，返回翻译结果："""
            
            # 使用Google翻译API
            params = {
                "client": "gtx",
                "sl": "auto",
                "tl": target_language,
                "dt": "t",
                "q": current_text
            }
            
            # 创建 session，保持SSL验证
            session = requests.Session()
            
            # 设置超时和重试
            response = session.get(
                self.base_url, 
                params=params, 
                timeout=self.timeout,
                headers={
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                }
            )
            response.raise_for_status()
            
            result = response.json()
            if result and len(result) > 0 and len(result[0]) > 0:
                translated_parts = [item[0] for item in result[0] if item[0]]
                translated_text = "".join(translated_parts)
                if translated_text and translated_text.strip():
                    return translated_text.strip()
                else:
                    print(f"Google 翻译返回空结果，使用原文: {current_text}")
                    return current_text
            else:
                print(f"Google 翻译返回无效结果，使用原文: {current_text}")
                return current_text
                
        except requests.exceptions.SSLError as e:
            print(f"Google 上下文翻译 SSL 证书验证失败: {e}")
            raise e
        except Exception as e:
            print(f"Google 上下文翻译失败: {e}，使用原文: {current_text}")
            return current_text
    
    def translate_text(self, text: str, target_language: str) -> str:
        """使用 Google 翻译 API"""
        try:
            params = {
                "client": "gtx",
                "sl": "auto",  # 自动检测源语言
                "tl": target_language,
                "dt": "t",
                "q": text
            }
            
            # 创建 session，保持SSL验证
            session = requests.Session()
            
            # 设置超时和重试
            response = session.get(
                self.base_url, 
                params=params, 
                timeout=self.timeout,
                headers={
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                }
            )
            response.raise_for_status()
            
            result = response.json()
            if result and len(result) > 0 and len(result[0]) > 0:
                translated_parts = [item[0] for item in result[0] if item[0]]
                translated_text = "".join(translated_parts)
                if translated_text and translated_text.strip():
                    return translated_text
                else:
                    print("Google 翻译返回空结果")
                    return text
            else:
                print("Google 翻译返回无效结果")
                return text
                
        except requests.exceptions.SSLError as e:
            print(f"SSL 证书验证失败: {e}")
            raise e
        except requests.exceptions.RequestException as e:
            print(f"网络请求失败: {e}")
            raise e
        except Exception as e:
            print(f"Google 翻译失败: {e}")
            return text
    
    def _translate_with_fallback(self, text: str, target_language: str) -> str:
        """备用翻译方法"""
        try:
            # 使用不同的 Google 翻译端点
            fallback_url = "https://translate.google.com/translate_a/single"
            params = {
                "client": "gtx",
                "sl": "auto",
                "tl": target_language,
                "dt": "t",
                "q": text
            }
            
            # 保持SSL验证
            response = requests.get(
                fallback_url,
                params=params,
                timeout=self.timeout,
                headers={
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                }
            )
            
            if response.status_code == 200:
                result = response.json()
                if result and len(result) > 0 and len(result[0]) > 0:
                    translated_parts = [item[0] for item in result[0] if item[0]]
                    return "".join(translated_parts)
            
            return text
            
        except requests.exceptions.SSLError as e:
            print(f"备用翻译方法 SSL 证书验证失败: {e}")
            raise e
        except Exception as e:
            print(f"备用翻译方法也失败: {e}")
            return text


class OpenAITranslator(Translator):
    """OpenAI GPT 翻译器"""
    
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
        # 额外的翻译优化设置
        self.cache_enabled = bool(config_manager.get('translation.cache_enabled', True))
        self._cache: Dict[str, str] = {}
    
    def _translate_with_context(self, context_text: str, current_text: str, 
                              target_language: str, start_time: float, end_time: float) -> str:
        """基于上下文翻译当前文本"""
        try:
            import openai
            
            client = openai.OpenAI(
                api_key=self.api_key,
                base_url=self.base_url
            )
            
            # 获取目标语言名称
            language_names = {
                "en": "英语",
                "zh": "中文",
                "ja": "日语",
                "ko": "韩语",
                "fr": "法语",
                "de": "德语",
                "es": "西班牙语",
                "ru": "俄语"
            }
            
            target_lang_name = language_names.get(target_language, target_language)
            
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
                print(f"OpenAI 翻译返回空结果，使用原文: {current_text}")
                return current_text
                
        except Exception as e:
            print(f"OpenAI 上下文翻译失败: {e}，使用原文: {current_text}")
            return current_text
    
    def translate_text(self, text: str, target_language: str) -> str:
        """使用 OpenAI GPT 进行翻译"""
        try:
            import openai
            
            client = openai.OpenAI(
                api_key=self.api_key,
                base_url=self.base_url
            )
            
            # 获取目标语言名称
            language_names = {
                "en": "英语",
                "zh": "中文",
                "ja": "日语",
                "ko": "韩语",
                "fr": "法语",
                "de": "德语",
                "es": "西班牙语",
                "ru": "俄语"
            }
            
            target_lang_name = language_names.get(target_language, target_language)
            
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
            
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            print(f"OpenAI 翻译失败: {e}")
            return text

    def translate_texts(self, texts: List[str], target_language: str) -> List[str]:
        """OpenAI 批量翻译实现：
        - 复用同一客户端，减少连接开销
        - 文本去重与缓存，降低成本
        - 逐条调用 chat.completions 以避开批量的上下文串扰
        """
        import openai

        client = openai.OpenAI(
            api_key=self.api_key,
            base_url=self.base_url
        )

        language_names = {
            "en": "英语",
            "zh": "中文",
            "ja": "日语",
            "ko": "韩语",
            "fr": "法语",
            "de": "德语",
            "es": "西班牙语",
            "ru": "俄语"
        }
        target_lang_name = language_names.get(target_language, target_language)

        results: List[str] = []
        for text in texts:
            cache_key = f"{target_language}::" + text
            if self.cache_enabled and cache_key in self._cache:
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
                if self.cache_enabled:
                    self._cache[cache_key] = translated
                results.append(translated)
            except Exception as e:
                print(f"OpenAI 批量翻译失败: {e}，使用原文")
                results.append(text)

        return results


class SimpleTranslator(Translator):
    """简单翻译器（占位符）"""
    
    def translate_text(self, text: str, target_language: str) -> str:
        """简单翻译实现（实际项目中可以替换为其他翻译服务）"""
        # 这里只是一个示例，实际使用时需要替换为真实的翻译服务
        return f"[{target_language.upper()}] {text}"


class OfflineTranslator(Translator):
    """离线翻译器（使用本地翻译库）"""
    
    def __init__(self):
        self.translator = None
        self.translator_type = None
        self._init_translator()
    
    def _init_translator(self):
        """初始化离线翻译器"""
        # 从配置文件获取偏好设置
        config = config_manager.get_translator_config('offline')
        preferred_service = config.get('service', 'auto')
        
        if preferred_service == 'googletrans' or preferred_service == 'auto':
            try:
                from googletrans import Translator
                self.translator = Translator()
                self.translator_type = 'googletrans'
                print("使用 googletrans 离线翻译器")
                return
            except ImportError:
                pass
        
        if preferred_service == 'deep_translator' or preferred_service == 'auto':
            try:
                from deep_translator import GoogleTranslator
                self.translator = GoogleTranslator
                self.translator_type = 'deep_translator'
                print("使用 deep-translator 离线翻译器")
                return
            except ImportError:
                pass
        
        print("未找到离线翻译库，将使用简单翻译器")
        self.translator = None
        self.translator_type = None
    
    def _translate_with_context(self, context_text: str, current_text: str, 
                              target_language: str, start_time: float, end_time: float) -> str:
        """基于上下文翻译当前文本"""
        if self.translator is None:
            return f"[{target_language.upper()}] {current_text}"
        
        try:
            if self.translator_type == 'googletrans':
                result = self.translator.translate(current_text, dest=target_language)
                return result.text
            elif self.translator_type == 'deep_translator':
                translator = self.translator(source='auto', target=target_language)
                return translator.translate(current_text)
            else:
                return f"[{target_language.upper()}] {current_text}"
        except Exception as e:
            print(f"离线翻译失败: {e}")
            return f"[{target_language.upper()}] {current_text}"
    
    def translate_text(self, text: str, target_language: str) -> str:
        """使用离线翻译"""
        if self.translator is None:
            return f"[{target_language.upper()}] {text}"
        
        try:
            if self.translator_type == 'googletrans':
                result = self.translator.translate(text, dest=target_language)
                return result.text
            elif self.translator_type == 'deep_translator':
                translator = self.translator(source='auto', target=target_language)
                return translator.translate(text)
            else:
                return f"[{target_language.upper()}] {text}"
        except Exception as e:
            print(f"离线翻译失败: {e}")
            return f"[{target_language.upper()}] {text}"


class BaiduTranslator(Translator):
    """百度翻译器"""
    
    def __init__(self):
        self.config = config_manager.get_translator_config('baidu')
        self.app_id = self.config.get('app_id', '')
        self.secret_key = self.config.get('secret_key', '')
        
        if not self.app_id or not self.secret_key:
            raise ValueError("需要设置百度翻译的 app_id 和 secret_key")
    
    def translate_text(self, text: str, target_language: str) -> str:
        """使用百度翻译 API"""
        try:
            import hashlib
            import random
            import time
            
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
            
            response = requests.get(
                'https://fanyi-api.baidu.com/api/trans/vip/translate',
                params=params,
                timeout=10
            )
            
            result = response.json()
            if 'trans_result' in result:
                return result['trans_result'][0]['dst']
            else:
                return text
                
        except Exception as e:
            print(f"百度翻译失败: {e}")
            return text


class TencentTranslator(Translator):
    """腾讯翻译器"""
    
    def __init__(self):
        self.config = config_manager.get_translator_config('tencent')
        self.secret_id = self.config.get('secret_id', '')
        self.secret_key = self.config.get('secret_key', '')
        
        if not self.secret_id or not self.secret_key:
            raise ValueError("需要设置腾讯翻译的 secret_id 和 secret_key")
    
    def translate_text(self, text: str, target_language: str) -> str:
        """使用腾讯翻译 API"""
        try:
            # 这里需要实现腾讯云的签名算法
            # 由于比较复杂，这里提供一个简化版本
            print("腾讯翻译功能需要实现完整的签名算法")
            return text
        except Exception as e:
            print(f"腾讯翻译失败: {e}")
            return text


class AliyunTranslator(Translator):
    """阿里云翻译器"""
    
    def __init__(self):
        self.config = config_manager.get_translator_config('aliyun')
        self.access_key_id = self.config.get('access_key_id', '')
        self.access_key_secret = self.config.get('access_key_secret', '')
        
        if not self.access_key_id or not self.access_key_secret:
            raise ValueError("需要设置阿里云翻译的 access_key_id 和 access_key_secret")
    
    def translate_text(self, text: str, target_language: str) -> str:
        """使用阿里云翻译 API"""
        try:
            # 这里需要实现阿里云的签名算法
            # 由于比较复杂，这里提供一个简化版本
            print("阿里云翻译功能需要实现完整的签名算法")
            return text
        except Exception as e:
            print(f"阿里云翻译失败: {e}")
            return text


def get_translator(translator_type: str = "google", **kwargs) -> Translator:
    """
    获取翻译器实例
    
    Args:
        translator_type: 翻译器类型 (google, openai, simple, offline, baidu, tencent, aliyun)
        **kwargs: 翻译器参数
        
    Returns:
        翻译器实例
    """
    # 如果没有指定翻译器类型，使用配置文件中的默认值
    if translator_type == "google":
        return GoogleTranslator()
    elif translator_type == "openai":
        return OpenAITranslator(**kwargs)
    elif translator_type == "simple":
        return SimpleTranslator()
    elif translator_type == "offline":
        return OfflineTranslator()
    elif translator_type == "baidu":
        return BaiduTranslator()
    elif translator_type == "tencent":
        return TencentTranslator()
    elif translator_type == "aliyun":
        return AliyunTranslator()
    else:
        raise ValueError(f"不支持的翻译器类型: {translator_type}")


def get_available_translators() -> List[str]:
    """获取可用的翻译器列表"""
    return config_manager.get_available_translators()


def get_default_translator() -> str:
    """获取默认翻译器"""
    return config_manager.get_default_translator()
