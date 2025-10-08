@echo off
REM Video2SRT Windows 安装脚本

echo 🎯 Video2SRT 安装脚本
echo ======================

REM 检查 Python
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ 错误: 未找到 Python
    echo 请先安装 Python 3.9 或更高版本
    pause
    exit /b 1
)

echo ✅ 找到 Python

REM 检查 pip
pip --version >nul 2>&1
if errorlevel 1 (
    echo ❌ 错误: 未找到 pip
    echo 请先安装 pip
    pause
    exit /b 1
)

echo ✅ 找到 pip

REM 检查 ffmpeg
ffmpeg -version >nul 2>&1
if errorlevel 1 (
    echo ⚠️  警告: 未找到 ffmpeg
    echo 请从 https://ffmpeg.org/download.html 下载并添加到 PATH
    echo.
    set /p continue="是否继续安装? (y/N): "
    if /i not "%continue%"=="y" exit /b 1
) else (
    echo ✅ 找到 ffmpeg
)

REM 创建虚拟环境
echo.
echo 📦 创建虚拟环境...
python -m venv venv

REM 激活虚拟环境
echo 🔧 激活虚拟环境...
call venv\Scripts\activate.bat

REM 升级 pip
echo ⬆️  升级 pip...
python -m pip install --upgrade pip

REM 安装依赖
echo 📥 安装依赖...
pip install -r requirements.txt

REM 安装项目
echo 🔨 安装项目...
pip install -e .

echo.
echo 🎉 安装完成!
echo.
echo 使用方法:
echo   命令行: python run.py input.mp4
echo   图形界面: python run.py gui
echo.
echo 激活虚拟环境:
echo   venv\Scripts\activate.bat
echo.
echo 退出虚拟环境:
echo   deactivate
echo.
pause
