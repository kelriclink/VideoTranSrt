#!/bin/bash
# Video2SRT 快速安装脚本

echo "🎯 Video2SRT 安装脚本"
echo "======================"

# 检查 Python 版本
python_version=$(python3 --version 2>&1 | grep -o '[0-9]\+\.[0-9]\+')
if [ -z "$python_version" ]; then
    echo "❌ 错误: 未找到 Python 3"
    echo "请先安装 Python 3.9 或更高版本"
    exit 1
fi

echo "✅ 找到 Python $python_version"

# 检查 pip
if ! command -v pip3 &> /dev/null; then
    echo "❌ 错误: 未找到 pip3"
    echo "请先安装 pip"
    exit 1
fi

echo "✅ 找到 pip3"

# 检查 ffmpeg
if ! command -v ffmpeg &> /dev/null; then
    echo "⚠️  警告: 未找到 ffmpeg"
    echo "请安装 ffmpeg:"
    echo "  Ubuntu/Debian: sudo apt install ffmpeg"
    echo "  macOS: brew install ffmpeg"
    echo "  Windows: 下载并添加到 PATH"
    echo ""
    read -p "是否继续安装? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
else
    echo "✅ 找到 ffmpeg"
fi

# 创建虚拟环境
echo ""
echo "📦 创建虚拟环境..."
python3 -m venv venv

# 激活虚拟环境
echo "🔧 激活虚拟环境..."
source venv/bin/activate

# 升级 pip
echo "⬆️  升级 pip..."
pip install --upgrade pip

# 安装依赖
echo "📥 安装依赖..."
pip install -r requirements.txt

# 安装项目
echo "🔨 安装项目..."
pip install -e .

echo ""
echo "🎉 安装完成!"
echo ""
echo "使用方法:"
echo "  命令行: python run.py input.mp4"
echo "  图形界面: python run.py gui"
echo ""
echo "激活虚拟环境:"
echo "  source venv/bin/activate"
echo ""
echo "退出虚拟环境:"
echo "  deactivate"
