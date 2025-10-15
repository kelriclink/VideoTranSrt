# video2srt_native 子项目

本目录是与 Python 项目并行的 C/C++ 原生子项目，包含：
- `libs/core/` 核心库（JSON 解析、网络、格式化、FFmpeg、Whisper.cpp 等）
- `apps/cli/` 命令行程序入口（v2s_cli）
- `apps/qtgui/` 图形界面程序入口（Qt6 Widgets，实现 v2s_qt）
- 配置脚本：`configure.ps1`（Windows，自动检测 Qt/MinGW 与本地依赖）

快速开始（Windows，推荐 MinGW + Qt6 + Ninja）：

1) 准备依赖
- 安装 Qt 6（含 MinGW 组件），例如：`C:\Qt\6.10.0\mingw_64` 与 `C:\Qt\Tools\mingw1310_64`
- 在 `native/third_party` 下准备本地依赖：
  - `nlohmann_json`：`git clone --depth 1 -b v3.11.2 https://github.com/nlohmann/json.git native/third_party/nlohmann_json`
  - （可选）FFmpeg/whisper.cpp 按需放置

2) 执行配置脚本

```powershell
powershell -ExecutionPolicy Bypass -File .\configure.ps1 -QtRoot "C:\Qt" -BuildDir "build-qt-mingw" -Generator "Ninja" -BuildType "Release" -UseLocalDeps
```

完成后：
- CLI：`native/build-qt-mingw/apps/cli/v2s_cli.exe`
- GUI：`native/build-qt-mingw/apps/qtgui/v2s_qt.exe`

部署 Qt 运行库（GUI）：

```powershell
C:\Qt\6.10.0\mingw_64\bin\windeployqt.exe --compiler-runtime --release D:\kelric_soft\videotransrt\native\build-qt-mingw\apps\qtgui\v2s_qt.exe
```

手动 CMake（不使用脚本）示例见 `native/BUILD.md`。

依赖管理约定：
- 优先使用本地 `native/third_party`（通过 `-DV2S_USE_LOCAL_DEPS=ON` 与 `-DV2S_THIRD_PARTY_DIR=...`）
- 或关闭本地优先，使用包管理器（如 vcpkg）：`-DV2S_USE_LOCAL_DEPS=OFF`
- 直接指定 nlohmann_json 根目录：`-DNLOHMANN_JSON_ROOT=...`

不改动原则：不修改 `video2srt/`、`setup.py`、`pyproject.toml` 与现有 CI。后续如需 CI 将新增独立 workflow。

配置文件位置约定：
- 程序启动时会在“可执行文件同目录”解析相对路径。例如：`config/config.json` 会解析为 `<exe目录>/config/config.json`；`config/default_config.json` 会解析为 `<exe目录>/config/default_config.json`。
- 当保存模型目录等设置时，程序会在 `<exe目录>/config/` 下自动创建/更新配置文件。