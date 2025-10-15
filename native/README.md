# video2srt_native 子项目

本目录是一个与 Python 项目并行的 C/C++ 子项目（不改动原项目）。

构建（Windows，推荐 Ninja）：

1. 安装 CMake（>=3.20）、Ninja、MSVC 或 LLVM/Clang
2. 可选安装 vcpkg 以管理依赖库
3. 生成与构建：
   - `cmake -S native -B native/build -G "Ninja" -DCMAKE_BUILD_TYPE=Release`
   - `cmake --build native/build --target v2s_cli`
   - `cmake --build native/build --target v2s_qt`

生成产物：`native/build/v2s_cli(.exe)`

图形界面（Windows，Qt）：`native/build/apps/qtgui/<Config>/v2s_qt.exe` 或 `native/build/apps/qtgui/v2s_qt.exe`

目录结构：
- `libs/core/` 核心库（后续将接入 FFmpeg、OpenVINO、ONNX Runtime、whisper.cpp 等）
- `apps/cli/` 命令行程序入口
- `apps/qtgui/` 图形界面程序入口（Qt6 Widgets 实现，支持 MinGW/MSVC）
- `PLANNING.md` 详细规划书

不改动原则：不修改 `video2srt/`、`setup.py`、`pyproject.toml`、现有 CI。后续如需 CI 将新增独立 workflow 文件。