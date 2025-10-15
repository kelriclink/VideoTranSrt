# Video2SRT Native 构建（Windows / MinGW + Ninja）简版

本指南仅记录在 Windows 下使用 MinGW（Qt 提供的 mingw1310_64）与 Ninja 构建本项目的最简命令。

环境要求：
- Qt 6.10.0（含 mingw_64）
- MinGW 13.1.0 编译器（通常位于：C:\Qt\Tools\mingw1310_64\bin）
- Ninja 已安装（例如来自 Python 虚拟环境或自行安装）

编译器与工具路径示例：
- C 编译器（gcc）：C:\Qt\Tools\mingw1310_64\bin\gcc.exe
- C++ 编译器（g++）：C:\Qt\Tools\mingw1310_64\bin\g++.exe
- Qt 前缀路径（CMAKE_PREFIX_PATH）：C:\Qt\6.10.0\mingw_64
- windeployqt.exe：C:\Qt\6.10.0\mingw_64\bin\windeployqt.exe

1) 配置（Configure）：

cmake -S D:/kelric_soft/videotransrt/native -B D:/kelric_soft/videotransrt/native/build -G Ninja -D CMAKE_C_COMPILER="C:/Qt/Tools/mingw1310_64/bin/gcc.exe" -D CMAKE_CXX_COMPILER="C:/Qt/Tools/mingw1310_64/bin/g++.exe" -D CMAKE_BUILD_TYPE=Release -D CMAKE_PREFIX_PATH="C:/Qt/6.10.0/mingw_64" -D V2S_ENABLE_WHISPER=ON -D V2S_DEPLOY_ON_BUILD=ON -D V2S_WINDEPLOYQT_EXE="C:/Qt/6.10.0/mingw_64/bin/windeployqt.exe"

2) 构建（Build）：

（推荐）
cmake --build D:/kelric_soft/videotransrt/native/build --config Release

（并行构建，可选其一）
- 使用 CMake 的并行参数：
  cmake --build D:/kelric_soft/videotransrt/native/build --config Release -j
- 或向 Ninja 传递并行参数（需指定数值）：
  cmake --build D:/kelric_soft/videotransrt/native/build --config Release -- -j 8

注意：不要使用“-- -j”且不带数值，会被 Ninja 拒绝（要求 -j 后必须跟并行数）。

3) 产物位置：
- CLI：D:/kelric_soft/videotransrt/native/build/apps/cli/v2s_cli.exe
- GUI：D:/kelric_soft/videotransrt/native/build/apps/qtgui/v2s_qt.exe

说明：
- 使用 -D V2S_ENABLE_WHISPER=ON 可启用 Whisper 功能，当前以静态库链接，不需要额外 Whisper DLL。
- -D V2S_DEPLOY_ON_BUILD=ON 且设置 V2S_WINDEPLOYQT_EXE 后，将在构建后自动部署 Qt 运行库到 GUI 目录。

本指南面向 Windows 平台，涵盖两种主流构建路径：
- MinGW + Qt6 + Ninja（推荐）
- MSVC + vcpkg（可选）

同时支持本地 third_party 依赖（无需包管理器）与通过包管理器安装依赖两种方式。

## 系统要求

- Windows 10/11（64 位）
- CMake ≥ 3.20
- Ninja（建议作为生成器）
- Qt 6（例如 C:\Qt\6.10.0\mingw_64）
- MinGW 工具链（例如 C:\Qt\Tools\mingw1310_64）

可选：
- Visual Studio（如走 MSVC + vcpkg 路径）
- vcpkg 包管理器（如不使用本地 third_party）

## 安装构建工具

### 1. 安装 Qt 6（MinGW 组件）

使用 Qt 在线安装器安装 Qt 6，并选择 MinGW 64-bit 组件。例如安装到：
- Qt 库前缀：`C:\Qt\6.10.0\mingw_64`（lib/cmake/Qt6 在此目录下）
- MinGW 工具链：`C:\Qt\Tools\mingw1310_64`（包含 gcc.exe/g++.exe）

如果仅构建原生 GUI，不需要 MSVC。

### 2. 安装 Visual Studio（仅当使用 MSVC + vcpkg 路径）

下载并安装 [Visual Studio Community](https://visualstudio.microsoft.com/zh-hans/vs/community/) 或 [Visual Studio Build Tools](https://visualstudio.microsoft.com/zh-hans/downloads/#build-tools-for-visual-studio-2022)

确保安装以下组件：
- MSVC v143 编译器工具集
- Windows 10/11 SDK
- CMake 工具

### 3. 安装 CMake & Ninja

从 [CMake官网](https://cmake.org/download/) 下载并安装最新版本，或使用包管理器：

```powershell
# 使用 Chocolatey
choco install cmake

# 使用 Scoop
scoop install cmake

# 使用 winget
winget install Kitware.CMake
```

### 4. 安装 vcpkg（可选）

```powershell
# 克隆 vcpkg
git clone https://github.com/Microsoft/vcpkg.git C:\vcpkg

# 运行引导脚本
C:\vcpkg\bootstrap-vcpkg.bat

# 集成到 Visual Studio
C:\vcpkg\vcpkg integrate install

# 添加到环境变量 (可选)
$env:PATH += ";C:\vcpkg"
```

## 构建步骤（推荐：MinGW + Qt6 + Ninja）

本项目在 `native/` 目录下提供了自动配置脚本 `configure.ps1`，可自动：
- 检测 Qt 库前缀（mingw_64）用于 CMAKE_PREFIX_PATH
- 检测 MinGW 工具链（Tools\mingw*_64）用于 C/C++ 编译器
- 检测本地 third_party/nlohmann_json

### 1. 依赖获取

推荐使用 Git Submodule 管理 `native/third_party` 依赖：
- `native/third_party/nlohmann_json`（来源：nlohmann/json）
- `native/third_party/whisper.cpp`（来源：ggerganov/whisper.cpp）

初始化依赖（首次或新增 submodule 后）：
```powershell
git submodule update --init --recursive
```

更新到子模块远端最新（可选）：
```powershell
git submodule update --remote --recursive
```

备用：若不使用 Submodule，也可手动克隆依赖到指定路径：
```powershell
# nlohmann_json（示例：v3.11.2）
git clone --depth 1 -b v3.11.2 https://github.com/nlohmann/json.git native/third_party/nlohmann_json
 
# whisper.cpp（默认 master/main）
git clone https://github.com/ggerganov/whisper.cpp.git native/third_party/whisper.cpp
```

FFmpeg（可选）：如果需要核心库启用 FFmpeg 支持，确保 `native/third_party/ffmpeg/include` 和 `native/third_party/ffmpeg/lib` 正确存在。运行时请将对应 DLL（avcodec/avformat/avutil/swresample 等）放在可执行文件同目录或 PATH 中。

Whisper.cpp（可选）：本仓库默认通过 Git Submodule 引入；如未初始化，请运行：
```powershell
git submodule update --init native/third_party/whisper.cpp
```
具体构建选项请参阅上游项目文档。

### 2. 纯 CMake 构建与自动部署（推荐）

本项目已将“部署”集成到 CMake 中（Windows 平台）：
- GUI（v2s_qt）：构建后自动执行 `windeployqt` 并拷贝 MinGW 运行时 DLL
- CLI（v2s_cli）：构建后自动拷贝 FFmpeg 与 MinGW 运行时 DLL
- 两者都会自动拷贝 `config/default_config.json` 到可执行目录的 `config/` 子目录

常用配置与构建命令（仓库根目录执行）：

```powershell
cmake -S .\native -B .\native\build -G Ninja -DCMAKE_BUILD_TYPE=Release \
  -DV2S_USE_LOCAL_DEPS=ON \
  -DCMAKE_PREFIX_PATH="C:\Qt\6.10.0\mingw_64" \
  -DV2S_WINDEPLOYQT_EXE="C:\Qt\6.10.0\mingw_64\bin\windeployqt.exe"

cmake --build .\native\build --config Release
```

构建完成后：
- Qt GUI：`native/build/apps/qtgui/v2s_qt.exe`
- CLI：`native/build/apps/cli/v2s_cli.exe`

部署与拷贝结果：
- GUI 目录下包含 Qt 运行库与插件、MinGW 运行时 DLL、翻译文件（如 `translations/qt_zh_CN.qm`）
- CLI 目录下包含 FFmpeg 的 DLL（如 `avcodec-62.dll` 等）与 MinGW 运行时 DLL
- 两者目录下的 `config/` 子目录包含 `default_config.json`

可选开关与变量：
- `-DV2S_DEPLOY_ON_BUILD=OFF` 关闭自动部署（默认 ON）
- `-DV2S_WINDEPLOYQT_EXE=...` 指定 windeployqt.exe 路径（未指定时会尝试自动推断）
- `-DV2S_COPY_DEFAULT_CONFIG_ON_BUILD=OFF` 关闭默认配置拷贝（默认 ON）
- `-DV2S_DEFAULT_CONFIG_PATH="D:/path/to/default_config.json"` 指定默认配置文件来源路径（默认指向仓库根的 `config/default_config.json`）

> 注：若使用多配置生成器（如 Visual Studio），请移除 `-DCMAKE_BUILD_TYPE` 并在 `cmake --build` 时使用 `--config Release`/`Debug`。

### 3. 使用脚本自动配置与构建（可选）

在 `native` 目录下运行：

```powershell
powershell -ExecutionPolicy Bypass -File .\configure.ps1 -QtRoot "C:\Qt" -BuildDir "build-qt-mingw" -Generator "Ninja" -BuildType "Release" -UseLocalDeps
```

说明：
- `-QtRoot`：Qt 安装根目录（脚本会在其下递归查找 `mingw_64` 与 `Tools\mingw*_64`）
- `-BuildDir`：构建输出目录（单配置生成器会直接在该目录产出 exe）
- `-Generator`：推荐使用 Ninja
- `-BuildType`：`Release` 或 `Debug`
- `-UseLocalDeps`：开启后优先使用 `native/third_party` 下的依赖（默认开启）
- `-EnableWhisper`：开启 Whisper.cpp 支持（默认关闭）
- `-ConfigureOnly`：仅生成构建系统，不执行编译

常用示例：

```powershell
# Release 构建（本地 third_party）
powershell -ExecutionPolicy Bypass -File .\configure.ps1 -QtRoot "C:\Qt" -BuildDir "build-qt-mingw" -Generator "Ninja" -BuildType "Release" -UseLocalDeps

# Debug 构建（本地 third_party）
powershell -ExecutionPolicy Bypass -File .\configure.ps1 -QtRoot "C:\Qt" -BuildDir "build-qt-mingw-debug" -Generator "Ninja" -BuildType "Debug" -UseLocalDeps

# 仅配置，不编译
powershell -ExecutionPolicy Bypass -File .\configure.ps1 -QtRoot "C:\Qt" -BuildDir "build-qt-mingw" -Generator "Ninja" -BuildType "Release" -UseLocalDeps -ConfigureOnly

# 启用 Whisper
powershell -ExecutionPolicy Bypass -File .\configure.ps1 -QtRoot "C:\Qt" -BuildDir "build-qt-mingw" -Generator "Ninja" -BuildType "Release" -UseLocalDeps -EnableWhisper
```

成功后输出：
- Qt GUI：`native/build-qt-mingw/apps/qtgui/v2s_qt.exe`
- CLI：`native/build-qt-mingw/apps/cli/v2s_cli.exe`

### 4. 手动 CMake（不使用脚本）

```powershell
cd native
cmake -S . -B build-qt-mingw -G Ninja -DCMAKE_BUILD_TYPE=Release ^
  -DCMAKE_C_COMPILER="C:\Qt\Tools\mingw1310_64\bin\gcc.exe" ^
  -DCMAKE_CXX_COMPILER="C:\Qt\Tools\mingw1310_64\bin\g++.exe" ^
  -DCMAKE_PREFIX_PATH="C:\Qt\6.10.0\mingw_64" ^
  -DV2S_USE_LOCAL_DEPS=ON ^
  -DV2S_THIRD_PARTY_DIR="D:\kelric_soft\videotransrt\native\third_party" ^
  -DNLOHMANN_JSON_ROOT="D:\kelric_soft\videotransrt\native\third_party\nlohmann_json" ^
  -DV2S_ENABLE_WHISPER=OFF

cmake --build build-qt-mingw -j 18
```

如果不使用本地依赖（通过包管理器安装）：

```powershell
cmake -S . -B build-qt-mingw -G Ninja -DCMAKE_BUILD_TYPE=Release ^
  -DCMAKE_C_COMPILER="C:\Qt\Tools\mingw1310_64\bin\gcc.exe" ^
  -DCMAKE_CXX_COMPILER="C:\Qt\Tools\mingw1310_64\bin\g++.exe" ^
  -DCMAKE_PREFIX_PATH="C:\Qt\6.10.0\mingw_64" ^
  -DV2S_USE_LOCAL_DEPS=OFF
```

> 说明：当前 CMake 不再自动使用 FetchContent 获取 nlohmann_json。请使用本地 third_party 或包管理器。

### 1. 安装依赖

```powershell
# 进入项目目录
cd native

# 安装依赖 (使用 vcpkg)
vcpkg install --triplet x64-windows
```

### 5. 手动部署（仅当禁用自动部署或需自定义）

```powershell
# 将 Qt 运行库拷贝到 GUI 可执行文件目录
C:\Qt\6.10.0\mingw_64\bin\windeployqt.exe --compiler-runtime --release D:\kelric_soft\videotransrt\native\build-qt-mingw\apps\qtgui\v2s_qt.exe
```

### 6. 构建项目（MSVC 多配置示例）

```powershell
# 构建 Release 版本
cmake --build . --config Release

# 或构建 Debug 版本
cmake --build . --config Debug
```

## 运行程序

构建完成后，可执行文件位于：
- `build/apps/cli/Release/v2s_cli.exe` (Release版本)
- `build/apps/cli/Debug/v2s_cli.exe` (Debug版本)

GUI（Qt 版本，Windows）可执行文件位于：
- `native/build-qt-mingw/apps/qtgui/v2s_qt.exe`（Ninja/MinGW 单配置生成器）
- 或 `build/apps/qtgui/<Config>/v2s_qt.exe`（MSVC 多配置生成器）

### 基本用法

```powershell
# 查看帮助
.\v2s_cli.exe --help

# 检查系统能力
.\v2s_cli.exe --check

# 转换视频为字幕
.\v2s_cli.exe input.mp4

# 指定输出文件和语言
.\v2s_cli.exe input.mp4 -o output.srt -l zh

# 使用GPU加速
.\v2s_cli.exe input.mp4 --gpu

# 仅提取音频
.\v2s_cli.exe input.mp4 --audio-only -o audio.wav
```

### GUI 使用（Qt 版本）

```powershell
# 运行图形界面（Windows）
.\v2s_qt.exe
```

在 Qt GUI 中：
- 选择输入文件与输出文件；
- 设置输出格式（srt/vtt/ass）、语言（auto 或指定）、模型大小、是否启用 GPU、CPU 线程数、是否合并片段、是否生成双语字幕、是否仅提取音频；
- 点击“开始转换”并观察进度条与日志。

### 配置文件位置（重要）

程序的配置（如 `config/config.json` 与 `config/default_config.json`）按“可执行文件所在目录”为基准解析与保存：
- 读取时：`config/config.json` 等相对路径会解析为 `<exe目录>/config/config.json`；
- 保存时：会自动在 `<exe目录>/config/` 下创建或更新配置文件。

这样可确保将配置与程序放在同一目录，便于绿色部署与迁移。默认构建后会自动将仓库根的 `config/default_config.json` 拷贝到可执行目录的 `config/` 子目录，可通过 `-DV2S_COPY_DEFAULT_CONFIG_ON_BUILD=OFF` 关闭或用 `-DV2S_DEFAULT_CONFIG_PATH=...` 指定其他来源。

## 使用 MinGW + Qt6 构建与打包（补充说明）

### 前置条件

- 已安装 MinGW 工具链（如 C:\Qt\Tools\mingw1310_64）
- 已安装 Qt 6（如 C:\Qt\6.10.0\mingw_64），选择 MinGW 64-bit 组件
- 确认 Qt 的 MinGW 版本与项目 MinGW ABI 兼容（尽量使用相同版本的 GCC）

### 配置环境变量（可选但推荐）

```powershell
# 假设 Qt 安装到 C:\Qt\6.6.3\mingw_64
$env:QTDIR = "C:\\Qt\\6.6.3\\mingw_64"
$env:PATH  = "$env:QTDIR\\bin;$env:PATH"
```

### CMake 配置与构建（MinGW，备选示例）

```powershell
cd native
mkdir build-mingw
cd build-mingw

# 指定 Qt 的 CMAKE_PREFIX_PATH，以便 find_package(Qt6 ...) 正常工作
cmake .. -G "MinGW Makefiles" -DCMAKE_BUILD_TYPE=Release -DCMAKE_PREFIX_PATH=$env:QTDIR -DV2S_USE_LOCAL_DEPS=ON

# 构建
cmake --build . --parallel
```

构建完成后，Qt GUI 可执行文件位于：`native/build-mingw/apps/qtgui/v2s_qt.exe`

### 运行与部署（windeployqt，备选示例）

```powershell
# 使用 Qt 的部署工具拷贝必要的运行库和插件
windeployqt.exe .\apps\qtgui\v2s_qt.exe

# 复制 FFmpeg 运行时 DLL（项目已提供）
Copy-Item ..\third_party\ffmpeg\bin\*.dll .\apps\qtgui\ -Force

# 复制 MinGW 运行时 DLL（项目已提供）
Copy-Item ..\winlibs-gcc\mingw64\bin\libstdc++-6.dll .\apps\qtgui\ -Force
Copy-Item ..\winlibs-gcc\mingw64\bin\libgcc_s_seh-1.dll .\apps\qtgui\ -Force
Copy-Item ..\winlibs-gcc\mingw64\bin\libwinpthread-1.dll .\apps\qtgui\ -Force
Copy-Item ..\winlibs-gcc\mingw64\bin\libgomp-1.dll .\apps\qtgui\ -Force
```

说明：
- windeployqt 会自动拷贝 Qt 平台插件（如 platforms\qwindows.dll）与必需的 Qt DLL。
- FFmpeg DLL（avcodec-62.dll、avformat-62.dll、avutil-60.dll、swresample-6.dll 等）需随应用分发。
- MinGW 运行时 DLL 需与应用一起分发，否则用户环境可能缺失这些库。

### 常见问题

- 找不到 Qt6::Widgets：检查 CMAKE_PREFIX_PATH 指向 Qt 安装目录（包含 lib\cmake\Qt6）。
- 运行报错缺少平台插件：确保 windeployqt 已执行，或系统 PATH 包含 Qt 的 plugins 目录。
- ABI 不兼容导致崩溃：保证 Qt 的 MinGW 版本与项目的 MinGW 版本一致或尽量匹配。
- CMake 显示 `No CMAKE_CXX_COMPILER could be found`：确保已安装 MinGW 工具链，并在命令行或脚本中为 CMAKE_C/CXX_COMPILER 指定正确路径，或将 `C:\Qt\Tools\mingw*_64\bin` 加入 PATH。
- MinGW 下 WinHTTP 证书绕过编译错误：已在源码中使用有效的标志组合替代 `SECURITY_FLAG_IGNORE_ALL_CERT_ERRORS`，更新到最新代码后可编译。

## 故障排除（MSVC + vcpkg 路径）

### 1. CMake 找不到

确保 CMake 已添加到系统 PATH 环境变量中。

### vcpkg 依赖安装失败

- 检查网络连接
- 尝试使用代理：`vcpkg install --triplet x64-windows --x-use-aria2`
- 手动下载依赖包

### 编译错误

- 确保使用正确的 Visual Studio 版本
- 检查 Windows SDK 版本
- 清理构建目录：`rm -rf build` 然后重新构建

### 运行时错误

- 确保所有依赖库都已正确安装
- 检查 FFmpeg 和 Whisper.cpp 是否可用
- 使用 `--check` 参数检查系统能力
- GUI 环境下，如果语言列表为空，可能是未编译 Whisper 支持；功能仍可使用但无法自动列出语言。

## 开发模式（MSVC + vcpkg）

对于开发者，建议使用以下配置：

```powershell
# 启用详细输出和调试信息
cmake .. -DCMAKE_TOOLCHAIN_FILE=C:\vcpkg\scripts\buildsystems\vcpkg.cmake -DCMAKE_BUILD_TYPE=Debug -DCMAKE_VERBOSE_MAKEFILE=ON

# 使用多核编译
cmake --build . --config Debug --parallel
```

## 性能优化

- 使用 Release 构建获得最佳性能
- 启用 GPU 加速 (如果支持)
- 根据 CPU 核心数调整线程数
- 选择合适的 Whisper 模型大小平衡速度和准确性