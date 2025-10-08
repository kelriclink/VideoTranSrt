# SSL 证书问题解决方案

## 问题描述

在使用 Google 翻译功能时，可能会遇到以下错误：
```
<urlopen error [SSL: CERTIFICATE_VERIFY_FAILED] certificate verify failed: Hostname mismatch, certificate is not valid for 'hipublic.azureedge.net'.(ssl.c1018)>
```

## 解决方案

### 1. 自动修复（推荐）

项目已经内置了自动修复功能，包括：

- **SSL 证书验证绕过**：自动禁用 SSL 验证
- **备用翻译端点**：当主端点失败时自动切换到备用端点
- **智能翻译器选择**：根据网络环境自动选择最佳翻译器
- **错误恢复机制**：翻译失败时自动降级到简单翻译器

### 2. 手动选择翻译器

如果仍然遇到问题，可以手动指定翻译器类型：

```bash
# 使用离线翻译器（推荐）
python run.py input.mp4 --translate en --translator offline

# 使用简单翻译器（不进行实际翻译）
python run.py input.mp4 --translate en --translator simple

# 使用 OpenAI 翻译器（需要 API Key）
python run.py input.mp4 --translate en --translator openai
```

### 3. 安装离线翻译库

为了获得更好的离线翻译体验，可以安装额外的翻译库：

```bash
# 安装 googletrans（推荐）
pip install googletrans==4.0.0rc1

# 或者安装 deep-translator
pip install deep-translator>=1.11.0
```

### 4. 网络环境配置

如果网络环境特殊，可以尝试以下方法：

#### Windows 用户
```bash
# 设置环境变量禁用 SSL 验证
set PYTHONHTTPSVERIFY=0
python run.py input.mp4 --translate en
```

#### Linux/macOS 用户
```bash
# 设置环境变量禁用 SSL 验证
export PYTHONHTTPSVERIFY=0
python run.py input.mp4 --translate en
```

### 5. 代理设置

如果使用代理，可以设置环境变量：

```bash
# HTTP 代理
set HTTP_PROXY=http://proxy.example.com:8080
set HTTPS_PROXY=http://proxy.example.com:8080

# SOCKS 代理
set HTTP_PROXY=socks5://proxy.example.com:1080
set HTTPS_PROXY=socks5://proxy.example.com:1080
```

## 翻译器类型说明

| 翻译器类型 | 说明 | 优点 | 缺点 |
|------------|------|------|------|
| `google` | Google 翻译 API | 质量高，支持多语言 | 需要网络，可能有 SSL 问题 |
| `offline` | 离线翻译库 | 不依赖网络，稳定 | 需要额外安装库 |
| `openai` | OpenAI GPT | 翻译质量最高 | 需要 API Key，收费 |
| `simple` | 简单占位符 | 不会出错 | 不进行实际翻译 |

## 故障排除

### 问题1：仍然出现 SSL 错误
**解决方案**：使用离线翻译器
```bash
python run.py input.mp4 --translate en --translator offline
```

### 问题2：翻译结果不理想
**解决方案**：
1. 尝试不同的翻译器类型
2. 检查网络连接
3. 使用 OpenAI 翻译器（需要 API Key）

### 问题3：离线翻译器无法工作
**解决方案**：
```bash
pip install googletrans==4.0.0rc1
# 或者
pip install deep-translator>=1.11.0
```

## 最佳实践

1. **首次使用**：让程序自动选择翻译器
2. **网络不稳定**：使用 `--translator offline`
3. **高质量需求**：使用 `--translator openai`（需要 API Key）
4. **批量处理**：建议使用离线翻译器避免网络问题

## 联系支持

如果问题仍然存在，请：
1. 检查网络连接
2. 尝试不同的翻译器类型
3. 查看错误日志获取更多信息
4. 提交 Issue 到项目仓库
