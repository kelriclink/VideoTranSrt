# Whisper模型下载问题解决方案

## 问题描述

在运行 `python run.py gui` 时，可能会遇到以下错误：
```
模型下载详细错误: HTTP Error 404: Not Found
模型 large 下载进度: 0% - 下载失败: HTTP Error 404: Not Found
```

这是因为Whisper官方下载源可能不稳定或已更改。

## 解决方案

### 方案1: 使用GUI手动下载 (推荐)

1. 启动GUI: `python run.py gui`
2. 打开设置 → 模型管理
3. 点击"手动下载"按钮查看详细说明
4. 按照说明手动下载模型

### 方案2: 使用命令行工具

运行手动下载工具：
```bash
python manual_download.py base
```

### 方案3: 直接从HuggingFace下载

1. 访问模型页面：
   - tiny: https://huggingface.co/openai/whisper-tiny
   - base: https://huggingface.co/openai/whisper-base
   - small: https://huggingface.co/openai/whisper-small
   - medium: https://huggingface.co/openai/whisper-medium
   - large: https://huggingface.co/openai/whisper-large-v2

2. 点击 "Files and versions" 标签
3. 下载 `pytorch_model.bin` 文件
4. 重命名为对应的模型名 (如 `base.pt`)
5. 放入 `model` 文件夹

### 方案4: 使用自定义下载

1. 在GUI中点击"自定义下载"按钮
2. 输入模型下载URL
3. 开始下载

## 模型大小选择建议

| 模型 | 大小 | 速度 | 准确性 | 推荐场景 |
|------|------|------|--------|----------|
| tiny | 39MB | 最快 | 较低 | 快速测试 |
| base | 74MB | 快 | 中等 | **日常使用** |
| small | 244MB | 中等 | 较好 | 平衡需求 |
| medium | 769MB | 较慢 | 好 | 高质量需求 |
| large | 1550MB | 最慢 | 最好 | 专业用途 |

## 故障排除

### 问题1: 下载的模型无法使用
**解决方案**: 确保模型文件完整且格式正确
- 检查文件大小是否合理
- 确保文件扩展名为 `.pt`
- 重新下载模型

### 问题2: 网络连接问题
**解决方案**: 
- 检查网络连接
- 尝试使用VPN
- 使用手动下载方式

### 问题3: SSL证书问题
**解决方案**: 
- 程序已自动处理SSL问题
- 如果仍有问题，设置环境变量: `set PYTHONHTTPSVERIFY=0`

## 文件结构

```
videotransrt/
├── model/                    # 模型存储目录
│   ├── tiny.pt              # tiny模型
│   ├── base.pt              # base模型
│   ├── small.pt             # small模型
│   ├── medium.pt            # medium模型
│   └── large.pt             # large模型
├── manual_download.py        # 手动下载工具
└── download_models.py        # 备用下载工具
```

## 联系支持

如果问题仍然存在：
1. 检查网络连接
2. 尝试不同的下载方法
3. 查看错误日志获取更多信息
4. 使用手动下载方式
