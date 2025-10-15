#pragma once

#include "models.hpp"
#include <string>
#include <vector>
#include <memory>
#include <filesystem>
#include <optional>

namespace v2s {

/**
 * Whisper模型大小枚举
 */
enum class WhisperModelSize {
    TINY,
    BASE, 
    SMALL,
    MEDIUM,
    LARGE
};

/**
 * 转录配置
 */
struct TranscriptionConfig {
    WhisperModelSize model_size = WhisperModelSize::BASE;
    std::optional<std::string> language;  // 语言代码，空表示自动检测
    std::filesystem::path model_path;     // 模型文件路径
    bool use_gpu = false;                 // 是否使用GPU加速
    int n_threads = 4;                    // CPU线程数
    bool verbose = false;                 // 是否输出详细信息
    
    TranscriptionConfig() = default;
};

#if V2S_HAVE_WHISPER
// 直接使用whisper.h中的前向声明
#include <whisper.h>
#endif

/**
 * 语音转录器
 * 使用Whisper.cpp进行语音识别
 */
class Transcriber {
public:
    /**
     * 构造函数
     * @param config 转录配置
     */
    explicit Transcriber(const TranscriptionConfig& config = TranscriptionConfig{});
    
    /**
     * 析构函数
     */
    ~Transcriber();
    
    // 禁用拷贝构造和赋值
    Transcriber(const Transcriber&) = delete;
    Transcriber& operator=(const Transcriber&) = delete;
    
    // 支持移动构造和赋值
    Transcriber(Transcriber&& other) noexcept;
    Transcriber& operator=(Transcriber&& other) noexcept;
    
    /**
     * 加载Whisper模型
     * @return 是否加载成功
     */
    bool load_model();
    
    /**
     * 检查模型是否已加载
     * @return 是否已加载
     */
    bool is_model_loaded() const;
    
    /**
     * 转录音频文件
     * @param audio_path 音频文件路径（WAV格式，16kHz，单声道）
     * @param language 指定语言（可选，空表示自动检测）
     * @return 转录结果
     */
    TranscriptionResult transcribe(const std::filesystem::path& audio_path,
                                 const std::optional<std::string>& language = std::nullopt);
    
    /**
     * 获取模型信息
     * @return 模型信息
     */
    ModelInfo get_model_info() const;
    
    /**
     * 获取支持的语言列表
     * @return 语言代码列表
     */
    static std::vector<std::string> get_supported_languages();
    
    /**
     * 检查Whisper.cpp是否可用
     * @return 是否可用
     */
    static bool is_available();
    
    /**
     * 将模型大小枚举转换为字符串
     * @param size 模型大小
     * @return 字符串表示
     */
    static std::string model_size_to_string(WhisperModelSize size);
    
    /**
     * 将字符串转换为模型大小枚举
     * @param size_str 字符串表示
     * @return 模型大小枚举
     */
    static std::optional<WhisperModelSize> string_to_model_size(const std::string& size_str);

private:
    TranscriptionConfig config_;
    bool model_loaded_;
#if V2S_HAVE_WHISPER
    whisper_context* ctx_;
#endif
    
    /**
     * 初始化Whisper上下文
     * @return 是否成功
     */
    bool initialize_context();
    
    /**
     * 清理资源
     */
    void cleanup();
    
    /**
     * 获取模型文件路径
     * @return 模型文件路径
     */
    std::filesystem::path get_model_file_path() const;
    
    /**
     * 加载音频数据
     * @param audio_path 音频文件路径
     * @return 音频数据（float数组）
     */
    std::vector<float> load_audio_data(const std::filesystem::path& audio_path);
};

} // namespace v2s