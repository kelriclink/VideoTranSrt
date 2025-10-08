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


class Translator:
    """翻译器基类"""
    
    def translate_text(self, text: str, target_language: str) -> str:
        """翻译文本"""
        raise NotImplementedError
    
    def translate_segments(self, segments: List[Dict[str, Any]], 
                          target_language: str) -> List[Dict[str, Any]]:
        """
        翻译分段文本（基于上下文的智能翻译）
        
        Args:
            segments: 分段列表
            target_language: 目标语言
            
        Returns:
            翻译后的分段列表
        """
        if not segments:
            return []
        
        translated_segments = []
        context_window = 10  # 上下文窗口大小
        
        for i, segment in enumerate(segments):
            # 获取上下文
            start_idx = max(0, i - context_window // 2)
            end_idx = min(len(segments), i + context_window // 2 + 1)
            context_segments = segments[start_idx:end_idx]
            
            # 构建带时间戳的上下文文本
            context_text = self._build_context_text(context_segments, i - start_idx)
            
            # 翻译当前段
            translated_text = self._translate_with_context(
                context_text, 
                segment["text"], 
                target_language,
                segment["start"],
                segment["end"]
            )
            
            translated_segments.append({
                "start": segment["start"],
                "end": segment["end"],
                "text": translated_text
            })
        
        return translated_segments
    
    def _build_context_text(self, context_segments: List[Dict[str, Any]], 
                           current_index: int) -> str:
        """构建带时间戳的上下文文本"""
        context_parts = []
        
        for j, seg in enumerate(context_segments):
            timestamp = f"[{self._format_timestamp(seg['start'])}-{self._format_timestamp(seg['end'])}]"
            if j == current_index:
                context_parts.append(f"{timestamp} {seg['text']} [CURRENT]")
            else:
                context_parts.append(f"{timestamp} {seg['text']}")
        
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
