# Video2SRT 开发指南

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
