# 🎯 Video2SRT - 视频/音频转字幕生成器

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
