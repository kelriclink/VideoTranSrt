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
from .formatter import SRTFormatter
from .config_manager import config_manager
from .models import ProcessingConfig, ProcessingResult, TranscriptionResult, TranslationResult
from .reporter import Reporter
from .translator_manager import TranslatorManager
from .error_handler import ErrorHandler, resource_manager
from .output_formats import output_format_manager


class Video2SRT:
    """视频转字幕主类"""
    
    def __init__(self, model_size: str = None, translator_type: str = None, reporter: Reporter = None):
        """
        初始化 Video2SRT
        
        Args:
            model_size: Whisper 模型大小，None 表示使用配置文件中的设置
            translator_type: 翻译器类型，None 表示使用配置文件中的设置
            reporter: 日志和通知报告器，None 表示创建默认报告器
        """
        # 从配置文件获取默认值
        self.model_size = model_size or config_manager.get_whisper_model_size()
        self.translator_type = translator_type or config_manager.get_default_translator()
        
        # 初始化报告器
        self.reporter = reporter or Reporter()
        
        # 初始化错误处理器
        self.error_handler = ErrorHandler(self.reporter)
        
        # 获取模型路径
        model_path = config_manager.get_whisper_model_path()
        self.transcriber = Transcriber(self.model_size, model_path)
        self.translator_manager = TranslatorManager(reporter=self.reporter)
        
    def process(self, input_path: str, 
                output_path: Optional[str] = None,
                language: Optional[str] = None,
                translate: Optional[str] = None,
                bilingual: bool = False,
                output_format: str = 'srt',
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
            output_format: 输出格式 (srt, vtt, ass)
            
        Returns:
            生成的字幕文件路径
        """
        try:
            with self.error_handler.error_context({"input_path": str(input_path), "output_format": output_format}):
                input_path = Path(input_path)
                
                if not input_path.exists():
                    raise FileNotFoundError(f"输入文件不存在: {input_path}")
                
                # 确定输出路径和格式
                if output_path is None:
                    # 根据输出格式确定扩展名
                    format_config = output_format_manager.get_format_info(output_format)
                    output_path = input_path.with_suffix(format_config.extension)
                else:
                    output_path = Path(output_path)
                    # 从输出路径检测格式
                    detected_format = output_format_manager.detect_format_from_extension(output_path)
                    if detected_format:
                        output_format = detected_format
                
                def notify_status(message: str):
                    if status_callback:
                        try:
                            status_callback(message)
                        except Exception:
                            pass
                    else:
                        self.reporter.info(message)

                def notify_progress(value: int):
                    if progress_callback:
                        try:
                            progress_callback(value)
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
                    self.reporter.info("步骤2: 语音识别...")
                    transcription_result = self.transcriber.transcribe(audio_path, language)
                    segments = transcription_result.segments
                    detected_language = transcription_result.language
                    
                    self.reporter.info(f"检测到语言: {detected_language}")
                    self.reporter.info(f"识别到 {len(segments)} 个字幕段")
                    notify_progress(60)
                    
                    # 步骤3: 翻译（如果需要）
                    translation_result = None
                    if translate:
                        self.reporter.info(f"步骤3: 翻译为 {translate}...")
                        
                        try:
                            # 使用翻译器管理器进行翻译（带重试机制）
                            translation_result = self.translator_manager.translate_with_retry(
                                segments=segments,
                                target_language=translate,
                                source_language=detected_language,
                                preferred_translator=self.translator_type
                            )
                            self.reporter.info(f"翻译完成，使用翻译器: {translation_result.translator_name}")
                            notify_progress(80)
                            
                        except Exception as e:
                            self.reporter.error(f"翻译过程出错: {e}")
                            self.reporter.warning("跳过翻译")
                            translate = None
                    
                    # 步骤4: 格式化输出
                    self.reporter.info("步骤4: 生成字幕文件...")
                    
                    if bilingual and translation_result:
                        # 双语字幕
                        output_format_manager.convert_bilingual_segments(
                            segments, translation_result.segments, 
                            output_format, output_path,
                            title=input_path.stem
                        )
                    elif translation_result:
                        # 仅翻译字幕
                        output_format_manager.convert_segments(
                            translation_result.segments, 
                            output_format, output_path,
                            title=input_path.stem
                        )
                    else:
                        # 原文字幕
                        output_format_manager.convert_segments(
                            segments, 
                            output_format, output_path,
                            title=input_path.stem
                        )
                    
                    self.reporter.info(f"字幕文件已保存: {output_path}")
                    notify_progress(100)

                    return output_path
        
        except Exception as e:
            # 处理错误并清理资源
            error_info = self.error_handler.handle_error(e, {
                "input_path": str(input_path),
                "output_format": output_format,
                "translate": translate,
                "bilingual": bilingual
            })
            raise
    
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
        """
        获取支持的输出格式列表
        
        Returns:
            支持的格式列表
        """
        return output_format_manager.get_supported_formats()
    
    def is_supported_format(self, file_path: str) -> bool:
        """
        检查文件格式是否支持
        
        Args:
            file_path: 文件路径
            
        Returns:
            是否支持该格式
        """
        detected_format = output_format_manager.detect_format_from_extension(file_path)
        return detected_format is not None
