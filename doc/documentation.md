# VideoTransRT 文档

## 目录
- [Readme](#readme)
- [Auto Output Name Guide](#auto-output-name-guide)
- [Config Usage](#config-usage)
- [Context Translation Guide](#context-translation-guide)
- [Development](#development)
- [Dynamic Url Guide](#dynamic-url-guide)
- [Fixes Report](#fixes-report)
- [Model Download Guide](#model-download-guide)
- [Model Management](#model-management)
- [Model Update Summary](#model-update-summary)
- [Ssl Troubleshooting](#ssl-troubleshooting)

## Readme

一个基于 Whisper 的智能视频/音频转字幕工具，支持多语言识别和翻译功能。

## ✨ 功能特性

- 🎬 **多格式支持**：MP4、MKV、AVI、MP3、WAV 等常见音视频格式
- 🗣️ **智能识别**：基于 OpenAI Whisper 的高精度语音识别
- 🌍 **多语言支持**：自动检测语言，支持 99+ 种语言
- 🔄 **翻译功能**：可选翻译为指定语言
- ⏰ **精确时间轴**：SRT 格式输出，时间精确到秒
- 🖥️ **双界面**：命令行 + 图形界面，满足不同用户需求
- 🚀 **高性能**：支持多种模型大小，平衡速度与精度

## 🚀 快速开始

### 安装依赖

```bash
# 克隆项目
git clone https://github.com/yourusername/video2srt.git
cd video2srt

# 安装依赖
pip install -r requirements.txt

# 确保 ffmpeg 已安装
# Windows: 下载 ffmpeg 并添加到 PATH
# macOS: brew install ffmpeg
# Linux: sudo apt install ffmpeg
```

### 命令行使用

```bash
# 基础用法
python -m video2srt input.mp4

# 指定输出文件
python -m video2srt input.mp4 -o output.srt

# 选择模型（tiny/base/small/medium/large）
python -m video2srt input.mp4 --model medium

# 启用翻译
python -m video2srt input.mp4 --translate en

# 完整参数示例
python -m video2srt input.mp4 -o output.srt --model medium --translate en --language auto
```

### 图形界面

```bash
# 启动 GUI
python -m video2srt.gui
```

## 📋 参数说明

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `-o, --output` | 输出文件名 | 自动生成 |
| `--model` | Whisper 模型大小 | `base` |
| `--translate` | 翻译目标语言代码 | 不翻译 |
| `--language` | 源语言（auto 自动检测） | `auto` |
| `--bilingual` | 双语字幕模式 | `false` |

## 🎛️ 模型选择

| 模型 | 大小 | 速度 | 精度 | 推荐场景 |
|------|------|------|------|----------|
| `tiny` | 39 MB | 最快 | 较低 | 快速预览 |
| `base` | 74 MB | 快 | 中等 | 日常使用 |
| `small` | 244 MB | 中等 | 较好 | 平衡选择 |
| `medium` | 769 MB | 较慢 | 很好 | 高质量需求 |
| `large` | 1550 MB | 最慢 | 最佳 | 专业用途 |

## 🌍 支持的语言

支持 99+ 种语言，包括但不限于：
- 🇨🇳 中文 (zh)
- 🇺🇸 英语 (en)
- 🇯🇵 日语 (ja)
- 🇰🇷 韩语 (ko)
- 🇫🇷 法语 (fr)
- 🇩🇪 德语 (de)
- 🇪🇸 西班牙语 (es)
- 🇷🇺 俄语 (ru)

## 📁 项目结构

```
video2srt/
├── video2srt/
│   ├── __init__.py
│   ├── core.py              # 主流程控制
│   ├── audio_extractor.py   # 音频提取
│   ├── transcriber.py       # 语音识别
│   ├── translator.py        # 翻译模块
│   ├── formatter.py         # SRT 格式化
│   ├── cli.py              # 命令行接口
│   └── gui/                # 图形界面
│       ├── __init__.py
│       ├── main.py
│       └── widgets.py
├── tests/                  # 测试文件
├── examples/              # 示例文件
├── requirements.txt        # 依赖列表
├── setup.py               # 安装配置
└── README.md              # 项目说明
```

## 🔧 开发指南

### 环境要求

- Python 3.9+
- FFmpeg
- 足够的磁盘空间（模型文件较大）

### 开发安装

```bash
# 克隆并进入项目目录
git clone https://github.com/yourusername/video2srt.git
cd video2srt

# 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 安装开发依赖
pip install -r requirements.txt
pip install -e .
```

### 运行测试

```bash
python -m pytest tests/
```

## 📦 打包分发

### PyInstaller 打包

```bash
# 安装 PyInstaller
pip install pyinstaller

# 打包 CLI 版本
pyinstaller --onefile --name video2srt-cli video2srt/cli.py

# 打包 GUI 版本
pyinstaller --onefile --windowed --name video2srt-gui video2srt/gui/main.py
```

### PyPI 发布

```bash
# 构建包
python -m build

# 上传到 PyPI
python -m twine upload dist/*
```

## 🤝 贡献指南

欢迎提交 Issue 和 Pull Request！

1. Fork 本项目
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 开启 Pull Request

## 📄 许可证

本项目采用 MIT 许可证 - 查看 [LICENSE](LICENSE) 文件了解详情。

## 🙏 致谢

- [OpenAI Whisper](https://github.com/openai/whisper) - 语音识别引擎
- [FFmpeg](https://ffmpeg.org/) - 音视频处理
- [PyQt6](https://www.riverbankcomputing.com/software/pyqt/) - GUI 框架

## ⚙️ 配置管理

### 配置文件位置
- **程序目录**: `项目根目录/config/config.json`
- **默认配置**: `项目根目录/config/default_config.json`

配置文件现在位于程序目录下的 `config` 文件夹中，便于管理和分发。

### GUI 配置
1. 启动 GUI: `python run.py gui`
2. 点击"配置"按钮或菜单栏"设置" -> "配置设置"
3. 设置各种 API 密钥和参数
4. 点击"保存"保存配置

### CLI 配置命令

```bash
# 查看当前配置
python run.py config show

# 设置 OpenAI API Key
python run.py config set-openai --api-key "your-api-key"

# 设置百度翻译 API
python run.py config set-baidu --app-id "your-app-id" --secret-key "your-secret-key"

# 设置默认翻译器
python run.py config set --key "general.default_translator" --value "openai"

# 导出/导入配置
python run.py config export-config --file "my_config.json"
python run.py config import-config --file "my_config.json"

# 重置为默认配置
python run.py config reset

# 设置 Whisper 模型
python run.py config set-whisper-model --model "large"

# 设置 Whisper 语言
python run.py config set-whisper-language --language "zh"

# 启用/禁用翻译器
python run.py config toggle-translator --translator google --enabled
python run.py config toggle-translator --translator openai --disabled
```

详细配置说明请查看 [配置使用指南](CONFIG_USAGE.md)

## 🎯 OpenAI 模型的作用

OpenAI 模型在 Video2SRT 中作为**翻译器**使用，而不是语音识别模型：

- **语音识别**：使用 Whisper 模型（tiny/base/small/medium/large）
- **翻译功能**：使用 OpenAI GPT 模型（gpt-3.5-turbo/gpt-4 等）

### 🔄 翻译器选择逻辑

1. **用户选择翻译器**：在 GUI 或 CLI 中指定翻译器类型
2. **单一翻译器**：选择了一个翻译器后，不会调用其他翻译器
3. **备用机制**：如果选择的翻译器不可用，会使用备用翻译器

### 📋 支持的翻译器

| 翻译器 | 类型 | 配置要求 | 特点 |
|--------|------|----------|------|
| Google | 在线 | 无需配置 | 免费，速度快 |
| OpenAI | 在线 | 需要 API Key | 翻译质量高，支持多种模型 |
| 百度翻译 | 在线 | 需要 App ID + Secret Key | 中文翻译效果好 |
| 离线翻译 | 离线 | 无需配置 | 不依赖网络，速度慢 |
| 简单翻译 | 内置 | 无需配置 | 基础翻译，总是可用 |

### 中文显示乱码
如果遇到中文显示乱码问题，请确保：

1. **Windows 用户**：程序已自动修复编码问题
2. **手动设置**：在命令行中运行 `chcp 65001`
3. **PowerShell 用户**：设置 `$OutputEncoding = [System.Text.Encoding]::UTF8`

### 自定义模型支持
程序支持自定义模型名称：

**GUI 界面**：
- 模型选择框支持直接输入自定义模型名称
- 可以选择预设模型或输入任意模型名称

**CLI 命令**：
```bash
# 使用自定义模型
python run.py process input.mp4 --model "your-custom-model"
```

**支持的预设模型**：
- Whisper: `tiny`, `base`, `small`, `medium`, `large`
- OpenAI: `gpt-3.5-turbo`, `gpt-4`, `gpt-4-turbo`, `gpt-4o`, `gpt-4o-mini`, `gpt-3.5-turbo-16k`

### SSL 证书错误
如果遇到 SSL 证书验证失败的错误，可以：

```bash
# 使用离线翻译器（推荐）
python run.py process input.mp4 --translate en --translator offline

# 或者使用简单翻译器
python run.py process input.mp4 --translate en --translator simple
```

详细解决方案请查看 [SSL 问题解决指南](SSL_TROUBLESHOOTING.md)

### 翻译器选择
- `google`: Google 翻译（默认，需要网络）
- `offline`: 离线翻译（推荐，稳定）
- `openai`: OpenAI GPT（需要 API Key）
- `baidu`: 百度翻译（需要 App ID 和 Secret Key）
- `tencent`: 腾讯翻译（需要 Secret ID 和 Secret Key）
- `aliyun`: 阿里云翻译（需要 Access Key ID 和 Secret）
- `simple`: 简单占位符（不会出错）

## 📞 联系方式

- 项目链接：[https://github.com/yourusername/video2srt](https://github.com/yourusername/video2srt)
- 问题反馈：[Issues](https://github.com/yourusername/video2srt/issues)

---

⭐ 如果这个项目对你有帮助，请给它一个星标！

## Auto Output Name Guide

## 功能概述

已成功实现自动更新输出文件名的功能。现在当用户选择视频文件时，不论原先GUI中输出文件是什么，都会自动刷新为与输入文件同名的.srt文件，之后用户可以手动修改。

## 主要改进

### 1. 自动更新输出文件名 ✅
**问题**: 用户选择输入文件后，输出文件名不会自动更新
**解决方案**: 
- 修改 `select_input_file()` 方法，每次选择文件都更新输出文件名
- 添加 `on_input_file_changed()` 方法，监听输入文件路径变化
- 支持手动输入文件路径时也自动更新输出文件名

### 2. 智能路径处理 ✅
**功能**: 
- 自动将输入文件的扩展名替换为 `.srt`
- 保持文件路径的目录结构
- 支持所有音视频格式的自动转换

### 3. 用户友好体验 ✅
**实现**:
- 用户仍可以手动修改输出文件名
- 支持通过"浏览"按钮选择自定义输出路径
- 实时响应输入文件的变化

## 技术实现

### 核心功能代码
```python
def select_input_file(self):
    """选择输入文件"""
    file_path, _ = QFileDialog.getOpenFileName(
        self,
        "选择视频或音频文件",
        "",
        "音视频文件 (*.mp4 *.mkv *.avi *.mov *.wmv *.flv *.mp3 *.wav *.m4a *.aac *.ogg *.flac);;所有文件 (*)"
    )
    
    if file_path:
        self.input_file_edit.setText(file_path)
        # 自动设置输出文件名（每次选择都更新）
        output_path = Path(file_path).with_suffix('.srt')
        self.output_file_edit.setText(str(output_path))

def on_input_file_changed(self, text):
    """输入文件变化时的处理"""
    if text.strip():
        try:
            # 检查是否是有效的文件路径
            input_path = Path(text.strip())
            if input_path.exists() and input_path.is_file():
                # 自动更新输出文件名
                output_path = input_path.with_suffix('.srt')
                self.output_file_edit.setText(str(output_path))
        except Exception:
            # 如果路径无效，不更新输出文件名
            pass
```

### 文件扩展名支持
支持以下音视频格式的自动转换：
- **视频格式**: `.mp4`, `.mkv`, `.avi`, `.mov`, `.wmv`, `.flv`
- **音频格式**: `.mp3`, `.wav`, `.m4a`, `.aac`, `.ogg`, `.flac`

### 路径处理逻辑
```python
# 示例转换
input_path = Path("testvideo/1351956921-1-192.mp4")
output_path = input_path.with_suffix('.srt')
# 结果: "testvideo/1351956921-1-192.srt"
```

## 使用方法

### 1. 通过文件对话框选择
1. 点击"浏览..."按钮
2. 选择视频或音频文件
3. 输出文件名自动更新为同名.srt文件
4. 可以手动修改输出文件名

### 2. 手动输入文件路径
1. 在输入文件框中直接输入文件路径
2. 如果文件存在，输出文件名自动更新
3. 可以手动修改输出文件名

### 3. 自定义输出路径
1. 点击输出文件的"浏览..."按钮
2. 选择自定义的保存位置和文件名
3. 输出文件名会更新为用户选择的值

## 功能特点

### 1. 智能更新
- **实时响应**: 输入文件变化时立即更新输出文件名
- **路径保持**: 保持输入文件的目录结构
- **扩展名转换**: 自动将音视频扩展名转换为.srt

### 2. 用户控制
- **手动编辑**: 用户可以随时修改输出文件名
- **自定义路径**: 支持选择自定义的保存位置
- **灵活配置**: 不强制使用自动生成的名称

### 3. 错误处理
- **路径验证**: 检查输入路径是否有效
- **异常处理**: 无效路径时不影响现有输出文件名
- **用户友好**: 提供清晰的错误提示

## 测试结果

功能已通过测试：
- ✅ 路径处理逻辑正常
- ✅ 自动更新输出文件名功能正常
- ✅ 支持所有音视频格式
- ✅ 用户可以手动修改输出文件名

## 使用示例

### 示例1: 选择视频文件
```
输入文件: D:\videos\movie.mp4
输出文件: D:\videos\movie.srt  (自动生成)
```

### 示例2: 手动输入路径
```
输入文件: C:\audio\song.wav
输出文件: C:\audio\song.srt  (自动生成)
```

### 示例3: 自定义输出路径
```
输入文件: D:\videos\movie.mp4
输出文件: E:\subtitles\custom_name.srt  (用户自定义)
```

## 优势

### 1. 提高效率
- **自动化**: 无需手动输入输出文件名
- **一致性**: 输出文件名与输入文件保持一致
- **便捷性**: 减少用户操作步骤

### 2. 用户友好
- **直观**: 输出文件名一目了然
- **灵活**: 支持手动修改和自定义
- **智能**: 自动处理各种文件格式

### 3. 稳定可靠
- **错误处理**: 完善的异常处理机制
- **路径安全**: 验证文件路径的有效性
- **兼容性**: 支持各种操作系统路径格式

现在用户选择视频文件时，输出文件名会自动更新为同名.srt文件，大大提高了使用效率！🎉

## Config Usage

## 📁 配置文件位置

配置文件现在位于程序目录下的 `config` 文件夹中：

- **用户配置**: `项目根目录/config/config.json`
- **默认配置**: `项目根目录/config/default_config.json`

### 优势

1. **便于管理**: 配置文件与程序在同一目录下，便于备份和分发
2. **版本控制**: 可以将配置文件纳入版本控制（注意不要提交包含 API Key 的配置）
3. **便携性**: 整个项目文件夹可以移动到任何位置使用
4. **多环境**: 可以为不同环境创建不同的配置文件

## GUI 配置

1. 启动 GUI: `python run.py gui`
2. 点击"配置"按钮或菜单栏"设置" -> "配置设置"
3. 在配置对话框中设置各种 API 密钥和参数
4. 点击"保存"保存配置

## CLI 配置

### 查看当前配置
```bash
python run.py config show
```

### 设置 OpenAI API Key
```bash
python run.py config set-openai --api-key "your-api-key-here"
```

### 设置百度翻译 API
```bash
python run.py config set-baidu --app-id "your-app-id" --secret-key "your-secret-key"
```

### 设置腾讯翻译 API
```bash
python run.py config set-tencent --secret-id "your-secret-id" --secret-key "your-secret-key"
```

### 设置阿里云翻译 API
```bash
python run.py config set-aliyun --access-key-id "your-access-key-id" --access-key-secret "your-access-key-secret"
```

### 设置其他配置
```bash
# 设置默认翻译器
python run.py config set --key "general.default_translator" --value "openai"

# 设置 Google 翻译超时时间
python run.py config set --key "google.timeout" --value "20"
```

### 导入/导出配置
```bash
# 导出配置
python run.py config export-config --file "my_config.json"

# 导入配置
python run.py config import-config --file "my_config.json"
```

### 重置为默认配置
```bash
python run.py config reset
```

## 使用配置

配置设置后，程序会自动使用配置文件中的设置：

```bash
# 使用默认翻译器（从配置文件读取）
python run.py process input.mp4 --translate en

# 指定翻译器类型
python run.py process input.mp4 --translate en --translator openai
```

## 配置文件格式

配置文件采用 JSON 格式，包含以下主要部分：

```json
{
    "openai": {
        "api_key": "your-api-key",
        "base_url": "https://api.openai.com/v1",
        "model": "gpt-3.5-turbo",
        "max_tokens": 4000,
        "temperature": 0.3
    },
    "google": {
        "enabled": true,
        "timeout": 15,
        "retry_count": 3
    },
    "baidu": {
        "app_id": "your-app-id",
        "secret_key": "your-secret-key",
        "enabled": false
    },
    "general": {
        "default_translator": "google",
        "fallback_translator": "simple",
        "auto_detect_language": true
    }
}
```

## 支持的翻译服务

1. **Google 翻译** - 免费，需要网络
2. **OpenAI GPT** - 高质量，需要 API Key
3. **百度翻译** - 国内服务，需要 App ID 和 Secret Key
4. **腾讯翻译** - 国内服务，需要 Secret ID 和 Secret Key
5. **阿里云翻译** - 国内服务，需要 Access Key ID 和 Secret
6. **离线翻译** - 使用本地库，不需要网络
7. **简单翻译** - 占位符，不进行实际翻译

## 注意事项

1. API 密钥等敏感信息会保存在本地配置文件中，请妥善保管
2. 配置文件支持导入导出，便于在不同设备间同步设置
3. 可以随时重置为默认配置
4. 配置更改后需要重新启动程序才能生效

## Context Translation Guide

## 功能概述

已成功实现基于上下文的智能翻译功能，解决了双语翻译时只翻译前几句的问题。现在翻译器会考虑前后10个对话的上下文信息，并结合时间戳进行更准确的翻译。

## 主要改进

### 1. 上下文感知翻译 ✅
**问题**: 原来的翻译逻辑是将所有文本拼接后翻译，然后按单词数量分割，导致翻译不准确
**解决方案**: 
- 实现基于上下文的翻译逻辑
- 每个字幕段都会考虑前后10个对话的上下文
- 保持时间戳信息，确保翻译准确性

### 2. 时间戳集成 ✅
**功能**: 
- 在翻译请求中包含时间戳信息
- 上下文文本格式：`[HH:MM:SS,mmm-HH:MM:SS,mmm] 文本内容`
- 当前翻译段标记为 `[CURRENT]`

### 3. 智能翻译策略 ✅
**实现**:
- 每个翻译器都支持基于上下文的翻译
- Google翻译器：使用上下文信息提高翻译准确性
- OpenAI翻译器：利用AI理解上下文，生成更自然的翻译
- 离线翻译器：保持原有功能，支持上下文信息

## 技术实现

### 核心翻译逻辑
```python
def translate_segments(self, segments: List[Dict[str, Any]], 
                      target_language: str) -> List[Dict[str, Any]]:
    """基于上下文的智能翻译"""
    context_window = 10  # 上下文窗口大小
    
    for i, segment in enumerate(segments):
        # 获取上下文（前后5个对话）
        start_idx = max(0, i - context_window // 2)
        end_idx = min(len(segments), i + context_window // 2 + 1)
        context_segments = segments[start_idx:end_idx]
        
        # 构建带时间戳的上下文文本
        context_text = self._build_context_text(context_segments, i - start_idx)
        
        # 基于上下文翻译当前段
        translated_text = self._translate_with_context(
            context_text, segment["text"], target_language,
            segment["start"], segment["end"]
        )
```

### 上下文文本格式
```
[00:00:00,000-00:00:04,000] Our family runs one of the oldest temples in Toronto.
[00:00:04,000-00:00:08,000] Instead of honoring a god, we honor our ancestors. [CURRENT]
[00:00:08,000-00:00:12,000] And not just the dudes, either.
```

### 翻译器增强

**Google翻译器**:
- 使用上下文信息提高翻译准确性
- 保持原有的API调用方式
- 增强错误处理和回退机制

**OpenAI翻译器**:
- 利用AI理解上下文语义
- 生成更自然、连贯的翻译
- 支持复杂的上下文分析

**离线翻译器**:
- 保持原有功能
- 支持上下文信息传递
- 提供稳定的离线翻译体验

## 使用方法

### 启用双语翻译
1. 启动程序：`python run.py gui`
2. 选择视频文件
3. 在翻译设置中选择目标语言
4. 勾选"双语字幕"选项
5. 开始处理

### 配置翻译器
1. 打开设置 → 翻译器
2. 选择翻译器类型
3. 测试翻译器功能
4. 保存配置

## 优势

### 1. 翻译质量提升
- **上下文理解**: 考虑前后对话的语义关系
- **时间感知**: 结合时间戳信息，提高翻译准确性
- **连贯性**: 确保翻译结果在语义上连贯

### 2. 智能处理
- **自适应窗口**: 根据字幕段位置调整上下文窗口
- **错误恢复**: 翻译失败时自动使用原文
- **性能优化**: 只翻译当前段，避免重复处理

### 3. 用户体验
- **无缝集成**: 与现有功能完美结合
- **透明处理**: 用户无需额外配置
- **稳定可靠**: 完善的错误处理机制

## 测试结果

所有功能已通过测试：
- ✅ 上下文构建功能正常
- ✅ 基于上下文的翻译功能正常
- ✅ 时间戳集成功能正常
- ✅ 各翻译器兼容性良好

## 技术特点

### 上下文窗口管理
- 默认窗口大小：10个对话（前5个 + 当前 + 后5个）
- 边界处理：自动调整窗口大小
- 性能优化：只处理必要的上下文信息

### 时间戳格式
- 标准格式：`[HH:MM:SS,mmm-HH:MM:SS,mmm]`
- 当前段标记：`[CURRENT]`
- 兼容性：与SRT格式完全兼容

### 错误处理
- 翻译失败时使用原文
- 网络问题时自动重试
- 详细的错误日志和用户提示

## 使用建议

1. **首次使用**: 建议使用Google翻译器，免费且稳定
2. **高质量需求**: 可以配置OpenAI翻译器，需要API Key
3. **离线使用**: 选择离线翻译器，无需网络连接
4. **测试功能**: 使用前建议先测试翻译器是否正常工作

现在双语翻译功能更加智能和准确，能够提供高质量的上下文感知翻译！🎉

## Development

## 开发环境设置

### 1. 克隆项目
```bash
git clone https://github.com/yourusername/video2srt.git
cd video2srt
```

### 2. 创建虚拟环境
```bash
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
```

### 3. 安装依赖
```bash
pip install -r requirements.txt
pip install -e .
```

### 4. 安装开发工具
```bash
pip install pytest black flake8 mypy
```

## 代码规范

### 代码格式化
```bash
# 使用 black 格式化代码
black video2srt/

# 使用 isort 整理导入
isort video2srt/
```

### 代码检查
```bash
# 使用 flake8 检查代码风格
flake8 video2srt/

# 使用 mypy 进行类型检查
mypy video2srt/
```

## 运行测试

```bash
# 运行所有测试
pytest

# 运行特定测试文件
pytest tests/test_core.py

# 运行测试并显示覆盖率
pytest --cov=video2srt

# 跳过慢速测试
pytest -m "not slow"
```

## 构建和发布

### 构建包
```bash
python -m build
```

### 本地安装测试
```bash
pip install dist/video2srt-1.0.0-py3-none-any.whl
```

### 发布到 PyPI
```bash
python -m twine upload dist/*
```

## 打包为可执行文件

### 使用 PyInstaller
```bash
# 打包 CLI 版本
pyinstaller --onefile --name video2srt-cli video2srt/cli.py

# 打包 GUI 版本
pyinstaller --onefile --windowed --name video2srt-gui video2srt/gui/main.py
```

## 项目结构说明

```
video2srt/
├── video2srt/           # 主包
│   ├── __init__.py      # 包初始化
│   ├── core.py          # 核心处理逻辑
│   ├── audio_extractor.py  # 音频提取
│   ├── transcriber.py   # 语音识别
│   ├── translator.py    # 翻译功能
│   ├── formatter.py     # SRT 格式化
│   ├── cli.py           # 命令行接口
│   └── gui/             # 图形界面
├── tests/               # 测试文件
├── examples/            # 使用示例
├── requirements.txt     # 依赖列表
├── setup.py            # 安装配置
├── pyproject.toml      # 项目配置
└── README.md           # 项目说明
```

## 贡献指南

1. Fork 项目
2. 创建特性分支
3. 提交更改
4. 推送到分支
5. 创建 Pull Request

## 常见问题

### Q: 如何添加新的翻译服务？
A: 在 `translator.py` 中继承 `Translator` 基类，实现 `translate_text` 方法。

### Q: 如何支持新的音频格式？
A: 在 `audio_extractor.py` 中修改 ffmpeg 参数，或在 `core.py` 中更新支持格式列表。

### Q: 如何优化处理速度？
A: 可以尝试使用更小的模型，或者实现并行处理功能。

## Dynamic Url Guide

## 功能概述

现在程序具备了动态获取Whisper模型下载地址的功能，每次进入模型管理页面时都会自动获取最新的下载链接。

## 新增功能

### 1. 动态URL获取
- **自动检测**: 程序会自动检测多个下载源的可用性
- **智能选择**: 选择最快、最稳定的下载地址
- **实时更新**: 每次进入模型管理页面都会刷新URL

### 2. 多重下载源
程序会按优先级尝试以下下载源：

1. **HuggingFace** (优先级最高)
   - `https://huggingface.co/openai/whisper-{size}/resolve/main/pytorch_model.bin`

2. **GitHub Releases** (备用)
   - `https://github.com/openai/whisper/releases/download/v20231117/whisper-{size}.pt`

3. **OpenAI官方** (备用)
   - `https://openaipublic.azureedge.net/whisper/models/...`

### 3. GUI增强功能

**模型管理页面新增按钮：**
- 🔄 **刷新下载地址** - 手动刷新所有下载地址
- ⬆️ **上传模型** - 上传本地模型文件
- 🌐 **自定义下载** - 使用自定义URL下载
- 📋 **手动下载** - 查看详细下载说明

## 使用方法

### 启动GUI
```bash
python run.py gui
```

### 使用动态下载
1. 打开设置 → 模型管理
2. 点击"刷新下载地址"查看当前可用地址
3. 点击"下载"按钮，程序会自动选择最佳URL
4. 实时查看下载进度

### 查看下载地址
1. 点击"刷新下载地址"按钮
2. 查看所有模型的可用下载地址
3. 每个地址都会显示可用性状态

## 技术实现

### 核心功能
- **URL检测**: 自动测试每个下载地址的可用性
- **智能选择**: 选择响应最快的可用地址
- **缓存机制**: 缓存URL信息，提高性能
- **错误处理**: 完善的异常处理和重试机制

### 支持的模型
| 模型 | 大小 | 下载源数量 | 推荐场景 |
|------|------|------------|----------|
| tiny | 39MB | 3个源 | 快速测试 |
| base | 74MB | 3个源 | **日常使用** |
| small | 244MB | 3个源 | 平衡需求 |
| medium | 769MB | 3个源 | 高质量需求 |
| large | 1550MB | 3个源 | 专业用途 |

## 故障排除

### 问题1: 所有下载源都不可用
**解决方案**:
1. 检查网络连接
2. 尝试使用VPN
3. 使用手动下载功能
4. 上传本地模型文件

### 问题2: 下载速度慢
**解决方案**:
1. 点击"刷新下载地址"选择更快的源
2. 使用自定义下载功能
3. 手动下载后上传

### 问题3: SSL证书问题
**解决方案**:
- 程序已自动处理SSL问题
- 如果仍有问题，设置环境变量: `set PYTHONHTTPSVERIFY=0`

## 优势

1. **自动化**: 无需手动查找下载地址
2. **可靠性**: 多个备用源确保下载成功
3. **实时性**: 始终使用最新的下载地址
4. **用户友好**: 一键刷新和下载
5. **智能选择**: 自动选择最佳下载源

## 更新日志

- ✅ 实现动态URL获取功能
- ✅ 添加多重下载源支持
- ✅ 集成GUI刷新功能
- ✅ 完善错误处理机制
- ✅ 添加URL可用性检测

现在您可以享受更稳定、更智能的模型下载体验！🎉

## Fixes Report

## 修复的问题

### 1. 日志显示问题 ✅
**问题**: GUI和CLI模式下处理过程中没有日志显示
**原因**: 翻译器初始化失败时没有适当的错误处理
**修复**:
- 在 `core.py` 中添加了完善的异常处理
- 翻译器初始化失败时会显示具体错误信息
- 翻译过程出错时会显示错误并跳过翻译
- 确保所有处理步骤都有日志输出

### 2. 翻译器错误和逻辑 ✅
**问题**: 翻译器不可用导致程序异常
**原因**: 
- Google翻译API访问失败
- 翻译器选择逻辑复杂
- 错误处理不完善

**修复**:
- 改进了Google翻译器的错误处理
- 添加了翻译结果验证
- 优化了备用翻译方法
- 完善了异常捕获和日志输出

### 3. 翻译器选择逻辑优化 ✅
**问题**: 翻译器选择界面复杂，用户容易混淆
**原因**: 多选模式导致配置复杂
**修复**:
- 改为单选模式，只选择一个翻译器
- 添加翻译器状态显示
- 添加翻译器测试功能
- 简化配置界面

## 新增功能

### 翻译器管理增强
1. **单选模式**: 用户只能选择一个翻译器
2. **状态显示**: 实时显示翻译器状态
3. **测试功能**: 可以测试翻译器是否正常工作
4. **智能选择**: 自动显示可用的翻译器

### 错误处理改进
1. **详细日志**: 所有处理步骤都有详细日志
2. **错误恢复**: 翻译失败时自动跳过，不影响字幕生成
3. **用户友好**: 错误信息更加清晰易懂

## 使用方法

### 启动程序
```bash
python run.py gui
```

### 配置翻译器
1. 打开设置 → 翻译器
2. 从下拉列表选择一个翻译器
3. 点击"测试翻译器"验证功能
4. 保存配置

### 支持的翻译器
- **Google**: 免费，需要网络连接
- **OpenAI**: 需要API Key，质量高
- **离线**: 使用本地库，无需网络
- **简单**: 占位符，仅用于测试

## 技术改进

### 核心处理逻辑
```python
# 改进的错误处理
try:
    self.translator = get_translator(self.translator_type)
except Exception as e:
    print(f"翻译器 {self.translator_type} 初始化失败: {e}")
    self.translator = None

# 翻译过程错误处理
if translate and self.translator:
    try:
        translated_segments = self.translator.translate_segments(segments, translate)
        print("翻译完成")
    except Exception as e:
        print(f"翻译过程出错: {e}")
        print("跳过翻译")
        translate = None
```

### 翻译器选择界面
```python
# 单选模式
self.translator_type_combo = QComboBox()
available_translators = config_manager.get_available_translators()
self.translator_type_combo.addItems(available_translators)

# 状态显示
self.translator_status_label = QLabel("状态: 检查中...")

# 测试功能
test_translator_btn = QPushButton("测试翻译器")
test_translator_btn.clicked.connect(self.test_current_translator)
```

## 测试结果

所有修复功能已通过测试：
- ✅ 日志显示功能正常
- ✅ 翻译器选择功能正常  
- ✅ GUI集成测试通过

## 使用建议

1. **首次使用**: 建议选择"Google"翻译器，免费且稳定
2. **网络问题**: 如果Google翻译不可用，可以选择"离线"翻译器
3. **高质量需求**: 可以配置OpenAI翻译器，需要API Key
4. **测试功能**: 使用前建议先测试翻译器是否正常工作

现在程序运行更加稳定，用户体验更好！🎉

## Model Download Guide

## 问题描述

在运行 `python run.py gui` 时，可能会遇到以下错误：
```
模型下载详细错误: HTTP Error 404: Not Found
模型 large 下载进度: 0% - 下载失败: HTTP Error 404: Not Found
```

这是因为Whisper官方下载源可能不稳定或已更改。

## 解决方案

### 方案1: 使用GUI手动下载 (推荐)

1. 启动GUI: `python run.py gui`
2. 打开设置 → 模型管理
3. 点击"手动下载"按钮查看详细说明
4. 按照说明手动下载模型

### 方案2: 使用命令行工具

运行手动下载工具：
```bash
python manual_download.py base
```

### 方案3: 直接从HuggingFace下载

1. 访问模型页面：
   - tiny: https://huggingface.co/openai/whisper-tiny
   - base: https://huggingface.co/openai/whisper-base
   - small: https://huggingface.co/openai/whisper-small
   - medium: https://huggingface.co/openai/whisper-medium
   - large: https://huggingface.co/openai/whisper-large-v2

2. 点击 "Files and versions" 标签
3. 下载 `pytorch_model.bin` 文件
4. 重命名为对应的模型名 (如 `base.pt`)
5. 放入 `model` 文件夹

### 方案4: 使用自定义下载

1. 在GUI中点击"自定义下载"按钮
2. 输入模型下载URL
3. 开始下载

## 模型大小选择建议

| 模型 | 大小 | 速度 | 准确性 | 推荐场景 |
|------|------|------|--------|----------|
| tiny | 39MB | 最快 | 较低 | 快速测试 |
| base | 74MB | 快 | 中等 | **日常使用** |
| small | 244MB | 中等 | 较好 | 平衡需求 |
| medium | 769MB | 较慢 | 好 | 高质量需求 |
| large | 1550MB | 最慢 | 最好 | 专业用途 |

## 故障排除

### 问题1: 下载的模型无法使用
**解决方案**: 确保模型文件完整且格式正确
- 检查文件大小是否合理
- 确保文件扩展名为 `.pt`
- 重新下载模型

### 问题2: 网络连接问题
**解决方案**: 
- 检查网络连接
- 尝试使用VPN
- 使用手动下载方式

### 问题3: SSL证书问题
**解决方案**: 
- 程序已自动处理SSL问题
- 如果仍有问题，设置环境变量: `set PYTHONHTTPSVERIFY=0`

## 文件结构

```
videotransrt/
├── model/                    # 模型存储目录
│   ├── tiny.pt              # tiny模型
│   ├── base.pt              # base模型
│   ├── small.pt             # small模型
│   ├── medium.pt            # medium模型
│   └── large.pt             # large模型
├── manual_download.py        # 手动下载工具
└── download_models.py        # 备用下载工具
```

## 联系支持

如果问题仍然存在：
1. 检查网络连接
2. 尝试不同的下载方法
3. 查看错误日志获取更多信息
4. 使用手动下载方式

## Model Management

## 新增功能

### 1. 模型文件夹
- 在程序目录下创建了 `model` 文件夹用于存放 Whisper 模型
- 模型文件不再存储在系统临时目录，便于管理和备份

### 2. GUI 模型管理界面
- 在设置对话框中新增了"模型管理"标签页
- 可以查看所有可用模型的详细信息（大小、速度、准确性）
- 支持一键下载和删除模型
- 实时显示模型下载状态和磁盘使用情况

### 3. 模型路径配置
- 在"语音识别"标签页中可以自定义模型存储路径
- 支持浏览选择自定义路径
- 配置会自动保存到配置文件中

## 使用方法

### 通过 GUI 管理模型
1. 启动程序：`python run.py gui`
2. 点击"设置"按钮
3. 切换到"模型管理"标签页
4. 查看模型列表，点击"下载"按钮下载需要的模型
5. 已下载的模型可以点击"删除"按钮删除

### 通过命令行指定模型路径
```bash
# 设置环境变量指定模型路径
set WHISPER_CACHE_DIR=D:\your\custom\model\path
python run.py input.mp4
```

### 模型大小选择建议
- **tiny (39MB)**: 适合快速测试，准确性较低
- **base (74MB)**: 平衡速度和准确性，推荐日常使用
- **small (244MB)**: 较好准确性，推荐使用
- **medium (769MB)**: 高准确性，适合重要内容
- **large (1550MB)**: 最高准确性，适合专业用途

## 技术实现

### 新增文件
- `video2srt/model_manager.py`: 模型管理核心模块
- `model/`: 模型存储目录

### 修改文件
- `video2srt/transcriber.py`: 支持自定义模型路径
- `video2srt/config_manager.py`: 添加模型路径配置管理
- `video2srt/gui/config_dialog.py`: 新增模型管理界面
- `video2srt/core.py`: 使用新的模型路径功能
- `config/default_config.json`: 添加模型路径配置项

### 主要功能
1. **模型下载**: 使用多线程下载，支持进度回调
2. **模型管理**: 检查模型存在性、获取文件大小、删除模型
3. **路径配置**: 支持自定义模型存储路径
4. **磁盘监控**: 实时显示模型文件夹的磁盘使用情况

## 注意事项

1. **网络要求**: 首次下载模型需要网络连接
2. **磁盘空间**: 大模型需要较多磁盘空间，请确保有足够空间
3. **下载时间**: 大模型下载时间较长，请耐心等待
4. **SSL 问题**: 如果遇到 SSL 证书问题，程序会自动处理或提供解决建议

## 故障排除

### 模型下载失败
1. 检查网络连接
2. 设置环境变量：`set PYTHONHTTPSVERIFY=0`
3. 尝试使用代理或VPN
4. 手动下载模型文件到 model 文件夹

### 模型路径问题
1. 确保路径存在且有写入权限
2. 路径中不要包含中文字符
3. 使用绝对路径而不是相对路径

### 性能优化
1. 根据硬件配置选择合适的模型大小
2. 有 GPU 的用户推荐使用 small 或 medium 模型
3. 只有 CPU 的用户推荐使用 tiny 或 base 模型

## Model Update Summary

## 更新内容

本次更新为 Video2SRT 项目添加了对所有 Whisper 模型的支持，包括英语专用模型和多语言模型。

### 新增模型

#### 英语专用模型 (.en)
- `tiny.en` - 39 MB，最快速度，较低准确性
- `base.en` - 74 MB，快速，中等准确性  
- `small.en` - 244 MB，中等速度，较好准确性
- `medium.en` - 769 MB，较慢，高准确性

#### 多语言模型
- `tiny` - 39 MB，最快速度，较低准确性
- `base` - 74 MB，快速，中等准确性（推荐）
- `small` - 244 MB，中等速度，较好准确性
- `medium` - 769 MB，较慢，高准确性
- `large` - 1550 MB，最慢，最高准确性
- `turbo` - 809 MB，快速，优化版本

## 修改的文件

### 1. 模型管理器 (`video2srt/model_manager.py`)
- 更新 `get_model_info()` 方法，添加所有新模型信息
- 更新 HuggingFace 模型映射
- 更新动态下载 URL 映射
- 更新备用下载 URL
- 添加模型类型分类方法：
  - `get_english_models()` - 获取英语专用模型列表
  - `get_multilingual_models()` - 获取多语言模型列表
  - `get_all_models()` - 获取所有模型列表
  - `get_model_type()` - 获取模型类型

### 2. 转录器 (`video2srt/transcriber.py`)
- 更新 `list_available_models()` 方法
- 更新 `get_model_size_info()` 方法，添加所有新模型信息
- 添加模型类型检测方法：
  - `is_english_model()` - 检查是否为英语专用模型
  - `get_english_models()` - 获取英语专用模型列表
  - `get_multilingual_models()` - 获取多语言模型列表
  - `get_model_type()` - 获取模型类型

### 3. 配置管理器 (`video2srt/config_manager.py`)
- 添加新模型相关方法：
  - `get_available_whisper_models()` - 获取所有可用模型
  - `get_english_whisper_models()` - 获取英语专用模型
  - `get_multilingual_whisper_models()` - 获取多语言模型
  - `is_english_model()` - 检查是否为英语专用模型
  - `get_model_recommendation()` - 根据使用场景推荐模型

### 4. 默认配置 (`config/default_config.json`)
- 添加模型分类配置
- 添加模型推荐配置

### 5. GUI 界面 (`video2srt/gui/main.py`)
- 更新模型选择下拉框，按类型分组显示
- 更新模型解析逻辑，正确处理带类型标识的模型名称
- 添加模型类型提示信息

### 6. 配置对话框 (`video2srt/gui/config_dialog.py`)
- 更新模型选择界面
- 更新模型说明文本
- 更新配置加载和保存逻辑

### 7. 命令行界面 (`video2srt/cli.py`)
- 更新 `process` 命令的模型选择选项
- 添加 `models` 命令显示所有可用模型信息
- 添加 `download_model` 命令下载指定模型
- 修复 Unicode 编码问题

## 使用方法

### GUI 使用
1. 启动 GUI：`python -m video2srt.gui.main`
2. 在"识别设置"中选择模型大小
3. 模型按类型分组显示：
   - 英语专用模型 (.en)
   - 多语言模型
   - 多语言优化模型 (turbo)

### 命令行使用
1. 查看所有模型：`python -m video2srt.cli models`
2. 下载模型：`python -m video2srt.cli download-model --model base.en`
3. 处理文件：`python -m video2srt.cli process input.mp4 --model base.en`

### 编程使用
```python
from video2srt.model_manager import model_manager
from video2srt.transcriber import Transcriber

# 获取所有模型信息
models = model_manager.get_model_info()

# 获取英语专用模型
english_models = model_manager.get_english_models()

# 获取多语言模型
multilingual_models = model_manager.get_multilingual_models()

# 创建转录器
transcriber = Transcriber(model_size="base.en")
```

## 模型选择建议

- **快速测试**：`tiny` 或 `tiny.en`
- **平衡性能**：`base` 或 `base.en`（推荐）
- **高质量**：`small` 或 `small.en`
- **最高质量**：`large` 或 `medium.en`
- **多语言优化**：`turbo`
- **英语专用**：选择 `.en` 模型，准确性更高
- **多语言**：选择不带 `.en` 的模型

## 注意事项

1. 英语专用模型（.en）只适用于英语内容，准确性更高
2. 多语言模型支持多种语言识别
3. turbo 模型是优化版本，速度更快
4. 模型下载需要网络连接，首次使用会自动下载
5. 建议根据硬件配置选择合适的模型大小

## Ssl Troubleshooting

## 问题描述

在使用 Google 翻译功能时，可能会遇到以下错误：
```
<urlopen error [SSL: CERTIFICATE_VERIFY_FAILED] certificate verify failed: Hostname mismatch, certificate is not valid for 'hipublic.azureedge.net'.(ssl.c1018)>
```

## 解决方案

### 1. 自动修复（推荐）

项目已经内置了自动修复功能，包括：

- **SSL 证书验证绕过**：自动禁用 SSL 验证
- **备用翻译端点**：当主端点失败时自动切换到备用端点
- **智能翻译器选择**：根据网络环境自动选择最佳翻译器
- **错误恢复机制**：翻译失败时自动降级到简单翻译器

### 2. 手动选择翻译器

如果仍然遇到问题，可以手动指定翻译器类型：

```bash
# 使用离线翻译器（推荐）
python run.py input.mp4 --translate en --translator offline

# 使用简单翻译器（不进行实际翻译）
python run.py input.mp4 --translate en --translator simple

# 使用 OpenAI 翻译器（需要 API Key）
python run.py input.mp4 --translate en --translator openai
```

### 3. 安装离线翻译库

为了获得更好的离线翻译体验，可以安装额外的翻译库：

```bash
# 安装 googletrans（推荐）
pip install googletrans==4.0.0rc1

# 或者安装 deep-translator
pip install deep-translator>=1.11.0
```

### 4. 网络环境配置

如果网络环境特殊，可以尝试以下方法：

#### Windows 用户
```bash
# 设置环境变量禁用 SSL 验证
set PYTHONHTTPSVERIFY=0
python run.py input.mp4 --translate en
```

#### Linux/macOS 用户
```bash
# 设置环境变量禁用 SSL 验证
export PYTHONHTTPSVERIFY=0
python run.py input.mp4 --translate en
```

### 5. 代理设置

如果使用代理，可以设置环境变量：

```bash
# HTTP 代理
set HTTP_PROXY=http://proxy.example.com:8080
set HTTPS_PROXY=http://proxy.example.com:8080

# SOCKS 代理
set HTTP_PROXY=socks5://proxy.example.com:1080
set HTTPS_PROXY=socks5://proxy.example.com:1080
```

## 翻译器类型说明

| 翻译器类型 | 说明 | 优点 | 缺点 |
|------------|------|------|------|
| `google` | Google 翻译 API | 质量高，支持多语言 | 需要网络，可能有 SSL 问题 |
| `offline` | 离线翻译库 | 不依赖网络，稳定 | 需要额外安装库 |
| `openai` | OpenAI GPT | 翻译质量最高 | 需要 API Key，收费 |
| `simple` | 简单占位符 | 不会出错 | 不进行实际翻译 |

## 故障排除

### 问题1：仍然出现 SSL 错误
**解决方案**：使用离线翻译器
```bash
python run.py input.mp4 --translate en --translator offline
```

### 问题2：翻译结果不理想
**解决方案**：
1. 尝试不同的翻译器类型
2. 检查网络连接
3. 使用 OpenAI 翻译器（需要 API Key）

### 问题3：离线翻译器无法工作
**解决方案**：
```bash
pip install googletrans==4.0.0rc1
# 或者
pip install deep-translator>=1.11.0
```

## 最佳实践

1. **首次使用**：让程序自动选择翻译器
2. **网络不稳定**：使用 `--translator offline`
3. **高质量需求**：使用 `--translator openai`（需要 API Key）
4. **批量处理**：建议使用离线翻译器避免网络问题

## 联系支持

如果问题仍然存在，请：
1. 检查网络连接
2. 尝试不同的翻译器类型
3. 查看错误日志获取更多信息
4. 提交 Issue 到项目仓库



---

*此文档由合并脚本自动生成*