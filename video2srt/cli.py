"""
命令行接口模块
提供 CLI 工具
"""

import click
import sys
from pathlib import Path
from typing import List

from .core import Video2SRT
from .config_manager import config_manager


@click.group()
@click.version_option(version='1.0.0')
def cli():
    """Video2SRT - 视频/音频转字幕生成器"""
    pass


@cli.command()
@click.argument('input_file', type=click.Path(exists=True))
@click.option('-o', '--output', 'output_file', 
              help='输出字幕文件路径')
@click.option('--model', 'model_size', 
              type=click.Choice(['tiny.en', 'base.en', 'small.en', 'medium.en',
                               'tiny', 'base', 'small', 'medium', 'large']),
              default='base',
              help='Whisper 模型大小 (支持英语专用模型 .en 和多语言模型)')
@click.option('--language', 'source_language',
              help='源语言代码 (auto 表示自动检测)')
@click.option('--translate', 'target_language',
              help='翻译目标语言代码')
@click.option('--translator', 'translator_type',
              type=click.Choice(['google', 'openai', 'simple', 'offline', 'baidu', 'tencent', 'aliyun']),
              help='翻译器类型')
@click.option('--bilingual', is_flag=True,
              help='生成双语字幕')
@click.option('--batch', 'batch_files',
              multiple=True,
              help='批量处理多个文件')
@click.option('--output-dir', 'batch_output_dir',
              help='批量处理时的输出目录')
def process(input_file, output_file, model_size, source_language, 
           target_language, translator_type, bilingual, batch_files, batch_output_dir):
    """
    处理视频/音频文件，生成字幕
    
    支持多种音视频格式，基于 OpenAI Whisper 进行语音识别，
    可选择翻译功能，输出标准 SRT 字幕文件。
    
    示例:
        video2srt process input.mp4
        video2srt process input.mp4 -o output.srt --model medium
        video2srt process input.mp4 --translate en --bilingual
    """
    
    try:
        # 如果没有指定翻译器，使用配置文件中的默认值
        if translator_type is None:
            translator_type = config_manager.get_default_translator()
        
        # 创建处理器
        processor = Video2SRT(model_size=model_size, translator_type=translator_type)
        
        # 检查输入文件格式
        if not processor.is_supported_format(input_file):
            click.echo(f"错误: 不支持的文件格式: {input_file}", err=True)
            click.echo(f"支持的格式: {', '.join(processor.get_supported_formats())}", err=True)
            sys.exit(1)
        
        # 批量处理
        if batch_files:
            all_files = [input_file] + list(batch_files)
            click.echo(f"批量处理 {len(all_files)} 个文件...")
            
            results = processor.batch_process(
                all_files,
                output_dir=batch_output_dir,
                language=source_language,
                translate=target_language,
                bilingual=bilingual
            )
            
            click.echo(f"批量处理完成，生成了 {len(results)} 个字幕文件")
            for result in results:
                click.echo(f"  - {result}")
        
        # 单文件处理
        else:
            click.echo(f"开始处理: {input_file}")
            
            result_path = processor.process(
                input_file,
                output_path=output_file,
                language=source_language,
                translate=target_language,
                bilingual=bilingual
            )
            
            click.echo(f"处理完成: {result_path}")
    
    except FileNotFoundError as e:
        click.echo(f"错误: {e}", err=True)
        sys.exit(1)
    
    except KeyboardInterrupt:
        click.echo("\n用户中断操作", err=True)
        sys.exit(1)
    
    except Exception as e:
        click.echo(f"处理过程中出现错误: {e}", err=True)
        sys.exit(1)


@cli.group()
def config():
    """配置管理命令"""
    pass


@config.command()
def show():
    """显示当前配置"""
    click.echo("当前配置:")
    click.echo(f"配置文件: {config_manager.config_file}")
    click.echo(f"默认翻译器: {config_manager.get_default_translator()}")
    click.echo(f"备用翻译器: {config_manager.get_fallback_translator()}")
    click.echo(f"可用翻译器: {', '.join(config_manager.get_available_translators())}")
    
    # 显示 API 配置状态
    openai_key = config_manager.get_openai_api_key()
    click.echo(f"OpenAI API Key: {'已设置' if openai_key else '未设置'}")
    
    baidu_app_id = config_manager.get('baidu.app_id')
    click.echo(f"百度翻译: {'已配置' if baidu_app_id else '未配置'}")
    
    tencent_secret_id = config_manager.get('tencent.secret_id')
    click.echo(f"腾讯翻译: {'已配置' if tencent_secret_id else '未配置'}")
    
    aliyun_access_key = config_manager.get('aliyun.access_key_id')
    click.echo(f"阿里云翻译: {'已配置' if aliyun_access_key else '未配置'}")


@config.command()
@click.option('--key', required=True, help='配置键')
@click.option('--value', required=True, help='配置值')
def set(key, value):
    """设置配置值"""
    if config_manager.set(key, value):
        click.echo(f"已设置 {key} = {value}")
        config_manager.save_config()
    else:
        click.echo(f"设置失败: {key}", err=True)
        sys.exit(1)


@config.command()
@click.option('--key', required=True, help='配置键')
def get(key):
    """获取配置值"""
    value = config_manager.get(key)
    if value is not None:
        click.echo(f"{key} = {value}")
    else:
        click.echo(f"配置键不存在: {key}", err=True)
        sys.exit(1)


@config.command()
@click.option('--api-key', required=True, help='OpenAI API Key')
def set_openai(api_key):
    """设置 OpenAI API Key"""
    if config_manager.set_openai_api_key(api_key):
        config_manager.set_translator_enabled('openai', True)
        click.echo("OpenAI API Key 已设置并启用")
        config_manager.save_config()
    else:
        click.echo("设置失败", err=True)
        sys.exit(1)


@config.command()
@click.option('--app-id', required=True, help='百度翻译 App ID')
@click.option('--secret-key', required=True, help='百度翻译 Secret Key')
def set_baidu(app_id, secret_key):
    """设置百度翻译 API"""
    config_manager.set('translators.baidu.app_id', app_id)
    config_manager.set('translators.baidu.secret_key', secret_key)
    config_manager.set_translator_enabled('baidu', True)
    config_manager.save_config()
    click.echo("百度翻译 API 已设置并启用")


@config.command()
@click.option('--secret-id', required=True, help='腾讯云 Secret ID')
@click.option('--secret-key', required=True, help='腾讯云 Secret Key')
def set_tencent(secret_id, secret_key):
    """设置腾讯翻译 API"""
    config_manager.set('tencent.secret_id', secret_id)
    config_manager.set('tencent.secret_key', secret_key)
    config_manager.set_translator_enabled('tencent', True)
    config_manager.save_config()
    click.echo("腾讯翻译 API 已设置")


@config.command()
@click.option('--access-key-id', required=True, help='阿里云 Access Key ID')
@click.option('--access-key-secret', required=True, help='阿里云 Access Key Secret')
def set_aliyun(access_key_id, access_key_secret):
    """设置阿里云翻译 API"""
    config_manager.set('aliyun.access_key_id', access_key_id)
    config_manager.set('aliyun.access_key_secret', access_key_secret)
    config_manager.set_translator_enabled('aliyun', True)
    config_manager.save_config()
    click.echo("阿里云翻译 API 已设置")


@config.command()
def reset():
    """重置为默认配置"""
    if click.confirm("确定要重置为默认配置吗？这将清除所有自定义设置。"):
        if config_manager.reset_to_default():
            click.echo("已重置为默认配置")
        else:
            click.echo("重置失败", err=True)
            sys.exit(1)
    else:
        click.echo("已取消重置")


@config.command()
@click.option('--file', 'file_path', required=True, help='配置文件路径')
def import_config(file_path):
    """导入配置文件"""
    if config_manager.import_config(file_path):
        click.echo("配置导入成功")
    else:
        click.echo("配置导入失败", err=True)
        sys.exit(1)


@config.command()
@click.option('--model', required=True, help='Whisper 模型大小')
def set_whisper_model(model):
    """设置 Whisper 模型大小"""
    if config_manager.set_whisper_model_size(model):
        click.echo(f"Whisper 模型已设置为: {model}")
        config_manager.save_config()
    else:
        click.echo("设置失败", err=True)
        sys.exit(1)


@config.command()
@click.option('--language', required=True, help='Whisper 语言设置')
def set_whisper_language(language):
    """设置 Whisper 语言"""
    if config_manager.set_whisper_language(language):
        click.echo(f"Whisper 语言已设置为: {language}")
        config_manager.save_config()
    else:
        click.echo("设置失败", err=True)
        sys.exit(1)


@config.command()
@click.option('--translator', required=True, help='翻译器名称')
@click.option('--enabled/--disabled', default=True, help='启用/禁用翻译器')
def toggle_translator(translator, enabled):
    """启用或禁用翻译器"""
    if config_manager.set_translator_enabled(translator, enabled):
        status = "启用" if enabled else "禁用"
        click.echo(f"{translator} 翻译器已{status}")
        config_manager.save_config()
    else:
        click.echo("设置失败", err=True)
        sys.exit(1)


@cli.command()
def models():
    """显示可用的 Whisper 模型信息"""
    from .model_manager import model_manager
    
    click.echo("可用的 Whisper 模型:")
    click.echo()
    
    models_info = model_manager.get_model_info()
    
    # 英语专用模型
    click.echo("英语专用模型 (.en):")
    english_models = ['tiny.en', 'base.en', 'small.en', 'medium.en']
    for model in english_models:
        if model in models_info:
            info = models_info[model]
            status = "已下载" if info['downloaded'] else "未下载"
            click.echo(f"  {model:10} | {info['size']:8} | {info['speed']:4} | {info['accuracy']:4} | {status}")
    
    click.echo()
    
    # 多语言模型
    click.echo("多语言模型:")
    multilingual_models = ['tiny', 'base', 'small', 'medium', 'large']
    for model in multilingual_models:
        if model in models_info:
            info = models_info[model]
            status = "已下载" if info['downloaded'] else "未下载"
            model_type = "多语言"
            click.echo(f"  {model:10} | {info['size']:8} | {info['speed']:4} | {info['accuracy']:4} | {model_type:4} | {status}")
    
    click.echo()
    click.echo("说明:")
    click.echo("  - .en 模型：英语专用，准确性更高")
    click.echo("  - 多语言模型：支持多种语言识别")
    click.echo("  - turbo：优化版本，速度更快")
    click.echo("  - 推荐：base 或 base.en (平衡速度和准确性)")


@cli.command()
@click.option('--model', 'model_size', required=True, 
              type=click.Choice(['tiny.en', 'base.en', 'small.en', 'medium.en',
                               'tiny', 'base', 'small', 'medium', 'large']),
              help='要下载的模型名称')
def download_model(model_size):
    """下载指定的 Whisper 模型"""
    from .model_manager import model_manager
    
    click.echo(f"开始下载模型: {model_size}")
    
    def progress_callback(model_name, progress, status):
        if progress == 100:
            click.echo(f"完成 {model_name}: {status}")
        else:
            click.echo(f"  {model_name}: {progress}% - {status}")
    
    success = model_manager.download_model(model_size, progress_callback)
    
    if success:
        click.echo(f"模型 {model_size} 下载完成")
    else:
        click.echo(f"模型 {model_size} 下载失败", err=True)
        sys.exit(1)


@cli.command()
def gui():
    """启动图形界面"""
    from .gui.main import main as gui_main
    gui_main()


def main():
    """主入口函数"""
    cli()


if __name__ == '__main__':
    main()
