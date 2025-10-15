# Video2SRT Native 构建指南

## 系统要求

- Windows 10/11
- Visual Studio 2019 或更新版本 (或 Visual Studio Build Tools)
- CMake 3.20 或更新版本
- vcpkg 包管理器

## 安装构建工具

### 1. 安装 Visual Studio

下载并安装 [Visual Studio Community](https://visualstudio.microsoft.com/zh-hans/vs/community/) 或 [Visual Studio Build Tools](https://visualstudio.microsoft.com/zh-hans/downloads/#build-tools-for-visual-studio-2022)

确保安装以下组件：
- MSVC v143 编译器工具集
- Windows 10/11 SDK
- CMake 工具

### 2. 安装 CMake

从 [CMake官网](https://cmake.org/download/) 下载并安装最新版本，或使用包管理器：

```powershell
# 使用 Chocolatey
choco install cmake

# 使用 Scoop
scoop install cmake

# 使用 winget
winget install Kitware.CMake
```

### 3. 安装 vcpkg

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

## 构建步骤

### 1. 安装依赖

```powershell
# 进入项目目录
cd native

# 安装依赖 (使用 vcpkg)
vcpkg install --triplet x64-windows
```

### 2. 配置项目

```powershell
# 创建构建目录
mkdir build
cd build

# 配置 CMake (使用 vcpkg)
cmake .. -DCMAKE_TOOLCHAIN_FILE=C:\vcpkg\scripts\buildsystems\vcpkg.cmake -DCMAKE_GENERATOR_PLATFORM=x64
```

### 3. 构建项目

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
- `build/apps/qtgui/Release/v2s_qt.exe` (Release 版本，MSVC 多配置生成器)
- `build/apps/qtgui/Debug/v2s_qt.exe` (Debug 版本，MSVC 多配置生成器)
- 或 `build/apps/qtgui/v2s_qt.exe`（单配置生成器，如 MinGW Makefiles/Ninja）

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

## 使用 MinGW + Qt6 构建与打包（推荐给当前项目）

### 前置条件

- 已安装 MinGW 工具链（与项目中的 winlibs-gcc/mingw64 版本兼容）
- 已安装 Qt 6（建议 6.5+），选择 MinGW 64-bit 组件
- 确认 Qt 的 MinGW 版本与项目 MinGW ABI 兼容（尽量使用相同版本的 GCC）

### 配置环境变量（可选但推荐）

```powershell
# 假设 Qt 安装到 C:\Qt\6.6.3\mingw_64
$env:QTDIR = "C:\\Qt\\6.6.3\\mingw_64"
$env:PATH  = "$env:QTDIR\\bin;$env:PATH"
```

### CMake 配置与构建（MinGW）

```powershell
cd native
mkdir build-mingw
cd build-mingw

# 指定 Qt 的 CMAKE_PREFIX_PATH，以便 find_package(Qt6 ...) 正常工作
cmake .. -G "MinGW Makefiles" -DCMAKE_BUILD_TYPE=Release -DCMAKE_PREFIX_PATH=$env:QTDIR

# 构建
cmake --build . --parallel
```

构建完成后，Qt GUI 可执行文件位于：`native/build-mingw/apps/qtgui/v2s_qt.exe`

### 运行与部署（windeployqt）

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

## 故障排除

### 1. CMake 找不到

确保 CMake 已添加到系统 PATH 环境变量中。

### 2. vcpkg 依赖安装失败

- 检查网络连接
- 尝试使用代理：`vcpkg install --triplet x64-windows --x-use-aria2`
- 手动下载依赖包

### 3. 编译错误

- 确保使用正确的 Visual Studio 版本
- 检查 Windows SDK 版本
- 清理构建目录：`rm -rf build` 然后重新构建

### 4. 运行时错误

- 确保所有依赖库都已正确安装
- 检查 FFmpeg 和 Whisper.cpp 是否可用
- 使用 `--check` 参数检查系统能力
- GUI 环境下，如果语言列表为空，可能是未编译 Whisper 支持；功能仍可使用但无法自动列出语言。

## 开发模式

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