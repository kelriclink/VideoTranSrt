# Video2SRT 示例脚本

"""
使用示例
"""

from video2srt import Video2SRT

def basic_example():
    """基础使用示例"""
    # 创建处理器
    processor = Video2SRT(model_size="base")
    
    # 处理单个文件
    result_path = processor.process("input.mp4")
    print(f"字幕文件已生成: {result_path}")

def translation_example():
    """翻译示例"""
    # 创建处理器
    processor = Video2SRT(model_size="medium", translator_type="google")
    
    # 处理并翻译
    result_path = processor.process(
        "input.mp4",
        language="zh",  # 源语言：中文
        translate="en",  # 翻译为英文
        bilingual=True   # 双语字幕
    )
    print(f"双语字幕文件已生成: {result_path}")

def batch_example():
    """批量处理示例"""
    processor = Video2SRT(model_size="small")
    
    # 批量处理
    input_files = ["video1.mp4", "video2.mp4", "video3.mp4"]
    results = processor.batch_process(
        input_files,
        output_dir="subtitles",
        translate="en"
    )
    
    print(f"批量处理完成，生成了 {len(results)} 个字幕文件")

if __name__ == "__main__":
    # 运行示例
    basic_example()
