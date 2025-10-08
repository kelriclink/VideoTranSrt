#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Video2SRT 启动脚本
"""

import sys
import os
import io
from pathlib import Path

# 强制设置UTF-8编码（修复Windows乱码问题）
if sys.platform.startswith('win'):
    # 设置标准输出编码
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')
    sys.stdin = io.TextIOWrapper(sys.stdin.buffer, encoding='utf-8')
    
    # 设置控制台代码页
    try:
        os.system('chcp 65001 > nul 2>&1')
    except:
        pass

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def main():
    """主函数"""
    if len(sys.argv) > 1 and sys.argv[1] == "gui":
        # 启动 GUI
        from video2srt.gui.main import main as gui_main
        gui_main()
    else:
        # 启动 CLI
        from video2srt.cli import main as cli_main
        cli_main()

if __name__ == "__main__":
    main()
