# 配置系统使用示例

## 📁 配置文件位置

配置文件现在位于程序目录下的 `config` 文件夹中：

- **用户配置**: `项目根目录/config/config.json`
- **默认配置**: `项目根目录/config/default_config.json`

### 优势

1. **便于管理**: 配置文件与程序在同一目录下，便于备份和分发
2. **版本控制**: 可以将配置文件纳入版本控制（注意不要提交包含 API Key 的配置）
3. **便携性**: 整个项目文件夹可以移动到任何位置使用
4. **多环境**: 可以为不同环境创建不同的配置文件

## GUI 配置

1. 启动 GUI: `python run.py gui`
2. 点击"配置"按钮或菜单栏"设置" -> "配置设置"
3. 在配置对话框中设置各种 API 密钥和参数
4. 点击"保存"保存配置

## CLI 配置

### 查看当前配置
```bash
python run.py config show
```

### 设置 OpenAI API Key
```bash
python run.py config set-openai --api-key "your-api-key-here"
```

### 设置百度翻译 API
```bash
python run.py config set-baidu --app-id "your-app-id" --secret-key "your-secret-key"
```

### 设置腾讯翻译 API
```bash
python run.py config set-tencent --secret-id "your-secret-id" --secret-key "your-secret-key"
```

### 设置阿里云翻译 API
```bash
python run.py config set-aliyun --access-key-id "your-access-key-id" --access-key-secret "your-access-key-secret"
```

### 设置其他配置
```bash
# 设置默认翻译器
python run.py config set --key "general.default_translator" --value "openai"

# 设置 Google 翻译超时时间
python run.py config set --key "google.timeout" --value "20"
```

### 导入/导出配置
```bash
# 导出配置
python run.py config export-config --file "my_config.json"

# 导入配置
python run.py config import-config --file "my_config.json"
```

### 重置为默认配置
```bash
python run.py config reset
```

## 使用配置

配置设置后，程序会自动使用配置文件中的设置：

```bash
# 使用默认翻译器（从配置文件读取）
python run.py process input.mp4 --translate en

# 指定翻译器类型
python run.py process input.mp4 --translate en --translator openai
```

## 配置文件格式

配置文件采用 JSON 格式，包含以下主要部分：

```json
{
    "openai": {
        "api_key": "your-api-key",
        "base_url": "https://api.openai.com/v1",
        "model": "gpt-3.5-turbo",
        "max_tokens": 4000,
        "temperature": 0.3
    },
    "google": {
        "enabled": true,
        "timeout": 15,
        "retry_count": 3
    },
    "baidu": {
        "app_id": "your-app-id",
        "secret_key": "your-secret-key",
        "enabled": false
    },
    "general": {
        "default_translator": "google",
        "fallback_translator": "simple",
        "auto_detect_language": true
    }
}
```

## 支持的翻译服务

1. **Google 翻译** - 免费，需要网络
2. **OpenAI GPT** - 高质量，需要 API Key
3. **百度翻译** - 国内服务，需要 App ID 和 Secret Key
4. **腾讯翻译** - 国内服务，需要 Secret ID 和 Secret Key
5. **阿里云翻译** - 国内服务，需要 Access Key ID 和 Secret
6. **离线翻译** - 使用本地库，不需要网络
7. **简单翻译** - 占位符，不进行实际翻译

## 注意事项

1. API 密钥等敏感信息会保存在本地配置文件中，请妥善保管
2. 配置文件支持导入导出，便于在不同设备间同步设置
3. 可以随时重置为默认配置
4. 配置更改后需要重新启动程序才能生效
