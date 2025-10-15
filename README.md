# VideoTransRT

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
git clone https://github.com/kelriclink/VideoTranSrt.git
cd VideoTranSrt

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

## 📄 许可证

本项目采用 MIT 许可证。详情请参阅 [LICENSE](LICENSE) 文件。

## 📚 更多文档

更多详细信息，请参阅 [文档目录](doc/documentation.md)：

- [配置使用指南](doc/md_backup/CONFIG_USAGE.md)
- [模型下载指南](doc/md_backup/MODEL_DOWNLOAD_GUIDE.md)
- [模型管理](doc/md_backup/MODEL_MANAGEMENT.md)
- [上下文翻译指南](doc/md_backup/CONTEXT_TRANSLATION_GUIDE.md)
- [开发文档](doc/md_backup/DEVELOPMENT.md)

## 🧩 原生（C++/Qt）构建

项目包含与 Python 并行的原生子项目（CLI 与 Qt GUI）。在 Windows 上现已支持“纯 CMake 一键构建并自动部署”。

快速开始（Windows，纯 CMake 自动部署）：

```powershell
# 在仓库根目录执行
cmake -S .\native -B .\native\build -G Ninja -DCMAKE_BUILD_TYPE=Release \
  -DV2S_USE_LOCAL_DEPS=ON \
  -DCMAKE_PREFIX_PATH="C:\Qt\6.10.0\mingw_64" \
  -DV2S_WINDEPLOYQT_EXE="C:\Qt\6.10.0\mingw_64\bin\windeployqt.exe"

cmake --build .\native\build --config Release
```

构建完成后：
- GUI：`native/build/apps/qtgui/v2s_qt.exe`（目录下已自动部署 Qt 运行库与所需 DLL）
- CLI：`native/build/apps/cli/v2s_cli.exe`（目录下已自动拷贝 FFmpeg 与 MinGW 运行时 DLL）
- 两者均会自动拷贝 `config/default_config.json` 至可执行目录的 `config/` 子目录（可关闭或自定义路径）

可选配置：
- `-DV2S_DEPLOY_ON_BUILD=OFF` 关闭自动部署（默认 ON）
- `-DV2S_WINDEPLOYQT_EXE=...` 指定 windeployqt.exe 路径（未指定时尝试自动推断）
- `-DV2S_COPY_DEFAULT_CONFIG_ON_BUILD=OFF` 关闭默认配置文件拷贝（默认 ON）
- `-DV2S_DEFAULT_CONFIG_PATH="D:/path/to/default_config.json"` 指定配置文件来源路径（默认为仓库根目录下的 `config/default_config.json`）

脚本方式（可选）：仍可使用 `native/configure.ps1` 自动检测 Qt/MinGW 与本地依赖完成配置与构建，详见 `native/BUILD.md`。

更多依赖管理与高级用法，请参阅 `native/BUILD.md` 与 `native/README.md`。