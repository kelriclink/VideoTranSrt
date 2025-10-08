# Video2SRT 模型更新总结

## 更新内容

本次更新为 Video2SRT 项目添加了对所有 Whisper 模型的支持，包括英语专用模型和多语言模型。

### 新增模型

#### 英语专用模型 (.en)
- `tiny.en` - 39 MB，最快速度，较低准确性
- `base.en` - 74 MB，快速，中等准确性  
- `small.en` - 244 MB，中等速度，较好准确性
- `medium.en` - 769 MB，较慢，高准确性

#### 多语言模型
- `tiny` - 39 MB，最快速度，较低准确性
- `base` - 74 MB，快速，中等准确性（推荐）
- `small` - 244 MB，中等速度，较好准确性
- `medium` - 769 MB，较慢，高准确性
- `large` - 1550 MB，最慢，最高准确性
- `turbo` - 809 MB，快速，优化版本

## 修改的文件

### 1. 模型管理器 (`video2srt/model_manager.py`)
- 更新 `get_model_info()` 方法，添加所有新模型信息
- 更新 HuggingFace 模型映射
- 更新动态下载 URL 映射
- 更新备用下载 URL
- 添加模型类型分类方法：
  - `get_english_models()` - 获取英语专用模型列表
  - `get_multilingual_models()` - 获取多语言模型列表
  - `get_all_models()` - 获取所有模型列表
  - `get_model_type()` - 获取模型类型

### 2. 转录器 (`video2srt/transcriber.py`)
- 更新 `list_available_models()` 方法
- 更新 `get_model_size_info()` 方法，添加所有新模型信息
- 添加模型类型检测方法：
  - `is_english_model()` - 检查是否为英语专用模型
  - `get_english_models()` - 获取英语专用模型列表
  - `get_multilingual_models()` - 获取多语言模型列表
  - `get_model_type()` - 获取模型类型

### 3. 配置管理器 (`video2srt/config_manager.py`)
- 添加新模型相关方法：
  - `get_available_whisper_models()` - 获取所有可用模型
  - `get_english_whisper_models()` - 获取英语专用模型
  - `get_multilingual_whisper_models()` - 获取多语言模型
  - `is_english_model()` - 检查是否为英语专用模型
  - `get_model_recommendation()` - 根据使用场景推荐模型

### 4. 默认配置 (`config/default_config.json`)
- 添加模型分类配置
- 添加模型推荐配置

### 5. GUI 界面 (`video2srt/gui/main.py`)
- 更新模型选择下拉框，按类型分组显示
- 更新模型解析逻辑，正确处理带类型标识的模型名称
- 添加模型类型提示信息

### 6. 配置对话框 (`video2srt/gui/config_dialog.py`)
- 更新模型选择界面
- 更新模型说明文本
- 更新配置加载和保存逻辑

### 7. 命令行界面 (`video2srt/cli.py`)
- 更新 `process` 命令的模型选择选项
- 添加 `models` 命令显示所有可用模型信息
- 添加 `download_model` 命令下载指定模型
- 修复 Unicode 编码问题

## 使用方法

### GUI 使用
1. 启动 GUI：`python -m video2srt.gui.main`
2. 在"识别设置"中选择模型大小
3. 模型按类型分组显示：
   - 英语专用模型 (.en)
   - 多语言模型
   - 多语言优化模型 (turbo)

### 命令行使用
1. 查看所有模型：`python -m video2srt.cli models`
2. 下载模型：`python -m video2srt.cli download-model --model base.en`
3. 处理文件：`python -m video2srt.cli process input.mp4 --model base.en`

### 编程使用
```python
from video2srt.model_manager import model_manager
from video2srt.transcriber import Transcriber

# 获取所有模型信息
models = model_manager.get_model_info()

# 获取英语专用模型
english_models = model_manager.get_english_models()

# 获取多语言模型
multilingual_models = model_manager.get_multilingual_models()

# 创建转录器
transcriber = Transcriber(model_size="base.en")
```

## 模型选择建议

- **快速测试**：`tiny` 或 `tiny.en`
- **平衡性能**：`base` 或 `base.en`（推荐）
- **高质量**：`small` 或 `small.en`
- **最高质量**：`large` 或 `medium.en`
- **多语言优化**：`turbo`
- **英语专用**：选择 `.en` 模型，准确性更高
- **多语言**：选择不带 `.en` 的模型

## 注意事项

1. 英语专用模型（.en）只适用于英语内容，准确性更高
2. 多语言模型支持多种语言识别
3. turbo 模型是优化版本，速度更快
4. 模型下载需要网络连接，首次使用会自动下载
5. 建议根据硬件配置选择合适的模型大小
