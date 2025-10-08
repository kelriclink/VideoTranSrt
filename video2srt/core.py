"""
核心处理模块
整合音频提取、语音识别、翻译和格式化功能
"""

import os
from pathlib import Path
from typing import Optional, List, Dict, Any
from tqdm import tqdm

from .audio_extractor import AudioExtractor
from .transcriber import Transcriber
from .translator import get_translator
from .formatter import SRTFormatter
from .network_utils import get_recommended_translator, test_translator
from .config_manager import config_manager


class Video2SRT:
    """视频转字幕主类"""
    
    def __init__(self, model_size: str = None, translator_type: str = None):
        """
        初始化 Video2SRT
        
        Args:
            model_size: Whisper 模型大小，None 表示使用配置文件中的设置
            translator_type: 翻译器类型，None 表示使用配置文件中的设置
        """
        # 从配置文件获取默认值
        self.model_size = model_size or config_manager.get_whisper_model_size()
        self.translator_type = translator_type or config_manager.get_default_translator()
        
        # 获取模型路径
        model_path = config_manager.get_whisper_model_path()
        self.transcriber = Transcriber(self.model_size, model_path)
        self.translator = None
        
    def process(self, input_path: str, 
                output_path: Optional[str] = None,
                language: Optional[str] = None,
                translate: Optional[str] = None,
                bilingual: bool = False,
                status_callback: Optional[Any] = None,
                progress_callback: Optional[Any] = None,
                log_callback: Optional[Any] = None) -> Path:
        """
        处理视频文件，生成字幕
        
        Args:
            input_path: 输入视频/音频文件路径
            output_path: 输出字幕文件路径
            language: 源语言（None 表示自动检测）
            translate: 翻译目标语言（None 表示不翻译）
            bilingual: 是否生成双语字幕
            
        Returns:
            生成的字幕文件路径
        """
        input_path = Path(input_path)
        
        if not input_path.exists():
            raise FileNotFoundError(f"输入文件不存在: {input_path}")
        
        # 确定输出路径
        if output_path is None:
            output_path = input_path.with_suffix('.srt')
        else:
            output_path = Path(output_path)
        
        def notify_status(message: str):
            if status_callback:
                try:
                    status_callback(message)
                except Exception:
                    pass
            if log_callback:
                try:
                    log_callback(message)
                except Exception:
                    pass
            else:
                print(message)

        def notify_progress(value: int):
            if progress_callback:
                try:
                    progress_callback(int(max(0, min(100, value))))
                except Exception:
                    pass

        notify_status(f"开始处理: {input_path}")
        notify_status(f"输出文件: {output_path}")
        notify_progress(5)
        
        # 步骤1: 提取音频
        notify_status("\n步骤1: 提取音频...")
        with AudioExtractor() as extractor:
            audio_path = extractor.extract_audio(input_path)
            notify_status(f"音频提取完成: {audio_path}")
            notify_progress(25)
            
            # 步骤2: 语音识别
            notify_status("\n步骤2: 语音识别...")
            result = self.transcriber.transcribe(audio_path, language)
            segments = self.transcriber.get_segments(result)
            detected_language = self.transcriber.get_language(result)
            
            notify_status(f"检测到语言: {detected_language}")
            notify_status(f"识别到 {len(segments)} 个字幕段")
            notify_progress(60)
            
            # 步骤3: 翻译（如果需要）
            translated_segments = None
            if translate:
                notify_status(f"\n步骤3: 翻译为 {translate}...")
                if self.translator is None:
                    # 使用指定的翻译器类型
                    notify_status(f"使用翻译器: {self.translator_type}")
                    try:
                        self.translator = get_translator(self.translator_type)
                    except Exception as e:
                        notify_status(f"翻译器 {self.translator_type} 初始化失败: {e}")
                        self.translator = None
                
                # 检查翻译器是否可用
                if self.translator is None:
                    notify_status(f"翻译器 {self.translator_type} 不可用，尝试使用备用翻译器")
                    fallback_translator = config_manager.get_fallback_translator()
                    try:
                        self.translator = get_translator(fallback_translator)
                        notify_status(f"使用备用翻译器: {fallback_translator}")
                    except Exception as e:
                        notify_status(f"备用翻译器 {fallback_translator} 也失败: {e}")
                        notify_status("所有翻译器都不可用，跳过翻译")
                        translate = None
                
                if translate and self.translator:
                    try:
                        translated_segments = self.translator.translate_segments(segments, translate)
                        notify_status("翻译完成")
                        notify_progress(80)
                    except Exception as e:
                        notify_status(f"翻译过程出错: {e}")
                        notify_status("跳过翻译")
                        translate = None
            
            # 步骤4: 格式化输出
            notify_status("\n步骤4: 生成字幕文件...")
            
            if bilingual and translated_segments:
                # 双语字幕
                srt_content = SRTFormatter.create_bilingual_srt(segments, translated_segments)
            elif translated_segments:
                # 单语翻译字幕
                srt_content = SRTFormatter.format_segments(translated_segments)
            else:
                # 原始字幕
                srt_content = SRTFormatter.format_segments(segments)
            
            # 保存文件
            SRTFormatter.save_srt(srt_content, output_path)
            notify_status(f"字幕文件已保存: {output_path}")
            notify_progress(100)
            
            return output_path
    
    def batch_process(self, input_files: List[str], 
                     output_dir: Optional[str] = None,
                     **kwargs) -> List[Path]:
        """
        批量处理多个文件
        
        Args:
            input_files: 输入文件列表
            output_dir: 输出目录
            **kwargs: 其他处理参数
            
        Returns:
            生成的字幕文件路径列表
        """
        if output_dir:
            output_dir = Path(output_dir)
            output_dir.mkdir(parents=True, exist_ok=True)
        
        results = []
        
        for input_file in tqdm(input_files, desc="批量处理"):
            try:
                # 确定输出路径
                input_path = Path(input_file)
                if output_dir:
                    output_path = output_dir / f"{input_path.stem}.srt"
                else:
                    output_path = None
                
                # 处理文件
                result_path = self.process(
                    input_file, 
                    output_path=str(output_path) if output_path else None,
                    **kwargs
                )
                results.append(result_path)
                
            except Exception as e:
                print(f"处理文件 {input_file} 时出错: {e}")
                continue
        
        return results
    
    def get_supported_formats(self) -> List[str]:
        """获取支持的输入格式"""
        return ['.mp4', '.mkv', '.avi', '.mov', '.wmv', '.flv', 
                '.mp3', '.wav', '.m4a', '.aac', '.ogg', '.flac']
    
    def is_supported_format(self, file_path: str) -> bool:
        """检查文件格式是否支持"""
        return Path(file_path).suffix.lower() in self.get_supported_formats()
