"""
网络连接检测工具
"""

import requests
import socket


def check_internet_connection() -> bool:
    """检查网络连接"""
    try:
        # 尝试连接到一个可靠的服务器
        socket.create_connection(("8.8.8.8", 53), timeout=3)
        return True
    except OSError:
        return False


def check_google_translate_access() -> bool:
    """检查 Google 翻译服务是否可访问"""
    try:
        response = requests.get(
            "https://translate.googleapis.com/translate_a/single",
            params={"client": "gtx", "sl": "en", "tl": "zh", "dt": "t", "q": "test"},
            timeout=5,
            verify=False
        )
        return response.status_code == 200
    except Exception:
        return False


def get_recommended_translator() -> str:
    """获取推荐的翻译器类型"""
    if not check_internet_connection():
        return "simple"
    
    if check_google_translate_access():
        return "google"
    else:
        return "offline"


def test_translator(translator_type: str) -> bool:
    """测试翻译器是否可用"""
    try:
        from .translator import get_translator
        
        translator = get_translator(translator_type)
        result = translator.translate_text("Hello", "zh")
        
        # 检查结果是否有效
        return result and len(result.strip()) > 0 and not result.startswith("[")
    except Exception as e:
        print(f"翻译器测试失败: {e}")
        return False
