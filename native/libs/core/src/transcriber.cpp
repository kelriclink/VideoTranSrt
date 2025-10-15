#include "video2srt_native/transcriber.hpp"
#include <iostream>
#include <fstream>
#include <sstream>
#include <algorithm>
#include "video2srt_native/model_manager.hpp"

#if V2S_HAVE_WHISPER
#include "whisper.h"
#endif

namespace v2s {

Transcriber::Transcriber(const TranscriptionConfig& config)
    : config_(config)
    , model_loaded_(false) {
#if V2S_HAVE_WHISPER
    ctx_ = nullptr;
#endif
}

Transcriber::~Transcriber() {
    cleanup();
}

Transcriber::Transcriber(Transcriber&& other) noexcept
    : config_(std::move(other.config_))
    , model_loaded_(other.model_loaded_) {
#if V2S_HAVE_WHISPER
    ctx_ = other.ctx_;
    other.ctx_ = nullptr;
#endif
    other.model_loaded_ = false;
}

Transcriber& Transcriber::operator=(Transcriber&& other) noexcept {
    if (this != &other) {
        cleanup();
        config_ = std::move(other.config_);
#if V2S_HAVE_WHISPER
        ctx_ = other.ctx_;
        other.ctx_ = nullptr;
#endif
        model_loaded_ = other.model_loaded_;
        other.model_loaded_ = false;
    }
    return *this;
}

bool Transcriber::load_model() {
#if V2S_HAVE_WHISPER
    if (model_loaded_) {
        return true;
    }
    
    std::filesystem::path model_file = get_model_file_path();
    
    if (!std::filesystem::exists(model_file)) {
        std::cerr << "模型文件不存在: " << model_file << std::endl;
        std::cerr << "请下载对应的Whisper模型文件" << std::endl;
        return false;
    }
    
    std::cout << "正在加载Whisper模型: " << model_file << std::endl;
    
    // 初始化Whisper参数
    whisper_context_params cparams = whisper_context_default_params();
    cparams.use_gpu = config_.use_gpu;
    
    // 加载模型
    ctx_ = whisper_init_from_file_with_params(model_file.string().c_str(), cparams);
    
    if (!ctx_) {
        std::cerr << "无法加载Whisper模型: " << model_file << std::endl;
        return false;
    }
    
    model_loaded_ = true;
    std::cout << "模型加载完成" << std::endl;
    return true;
#else
    std::cerr << "Whisper.cpp支持未启用，请重新编译并启用WHISPER特性" << std::endl;
    return false;
#endif
}

bool Transcriber::is_model_loaded() const {
    return model_loaded_;
}

TranscriptionResult Transcriber::transcribe(const std::filesystem::path& audio_path,
                                          const std::optional<std::string>& language) {
#if V2S_HAVE_WHISPER
    if (!model_loaded_) {
        if (!load_model()) {
            throw std::runtime_error("无法加载Whisper模型");
        }
    }
    
    if (!std::filesystem::exists(audio_path)) {
        throw std::runtime_error("音频文件不存在: " + audio_path.string());
    }
    
    std::cout << "开始转录: " << audio_path << std::endl;
    
    // 加载音频数据
    std::vector<float> audio_data = load_audio_data(audio_path);
    
    if (audio_data.empty()) {
        throw std::runtime_error("无法加载音频数据");
    }
    
    // 设置转录参数
    whisper_full_params wparams = whisper_full_default_params(WHISPER_SAMPLING_GREEDY);
    wparams.print_realtime = config_.verbose;
    wparams.print_progress = config_.verbose;
    wparams.print_timestamps = true;
    wparams.print_special = false;
    wparams.translate = false;
    wparams.n_threads = config_.n_threads;
    wparams.offset_ms = 0;
    wparams.no_context = true;
    wparams.single_segment = false;
    
    // 设置语言
    if (language.has_value() && !language->empty()) {
        wparams.language = language->c_str();
    }
    
    // 执行转录
    int result = whisper_full(ctx_, wparams, audio_data.data(), static_cast<int>(audio_data.size()));
    
    if (result != 0) {
        throw std::runtime_error("Whisper转录失败，错误代码: " + std::to_string(result));
    }
    
    // 提取结果
    TranscriptionResult transcription_result;
    transcription_result.model_name = model_size_to_string(config_.model_size);
    
    // 获取检测到的语言
    int lang_id = whisper_full_lang_id(ctx_);
    if (lang_id >= 0) {
        transcription_result.language = whisper_lang_str(lang_id);
    } else {
        transcription_result.language = "unknown";
    }
    
    // 提取分段
    int n_segments = whisper_full_n_segments(ctx_);
    transcription_result.segments.reserve(n_segments);
    
    std::ostringstream full_text;
    
    for (int i = 0; i < n_segments; ++i) {
        const char* text = whisper_full_get_segment_text(ctx_, i);
        int64_t start_time = whisper_full_get_segment_t0(ctx_, i);
        int64_t end_time = whisper_full_get_segment_t1(ctx_, i);
        
        // 转换时间（从Whisper的时间单位到秒）
        double start_seconds = static_cast<double>(start_time) / 100.0;
        double end_seconds = static_cast<double>(end_time) / 100.0;
        
        Segment segment;
        segment.start = start_seconds;
        segment.end = end_seconds;
        segment.text = text ? text : "";
        segment.language = transcription_result.language;
        
        // 简单的置信度估算（Whisper.cpp没有直接提供置信度）
        segment.confidence = 0.8;  // 默认置信度
        
        transcription_result.segments.push_back(segment);
        
        if (!segment.text.empty()) {
            full_text << segment.text;
            if (i < n_segments - 1) {
                full_text << " ";
            }
        }
    }
    
    transcription_result.text = full_text.str();
    
    std::cout << "转录完成，共 " << n_segments << " 个分段" << std::endl;
    
    return transcription_result;
#else
    throw std::runtime_error("Whisper.cpp支持未启用");
#endif
}

ModelInfo Transcriber::get_model_info() const {
    ModelInfo info;
    info.name = model_size_to_string(config_.model_size);
    info.type = "whisper.cpp";
    info.is_downloaded = model_loaded_;
    return info;
}

std::vector<std::string> Transcriber::get_supported_languages() {
#if V2S_HAVE_WHISPER
    std::vector<std::string> languages;
    
    // Whisper支持的主要语言
    const char* lang_codes[] = {
        "en", "zh", "de", "es", "ru", "ko", "fr", "ja", "pt", "tr", "pl", "ca", "nl", 
        "ar", "sv", "it", "id", "hi", "fi", "vi", "he", "uk", "el", "ms", "cs", "ro", 
        "da", "hu", "ta", "no", "th", "ur", "hr", "bg", "lt", "la", "mi", "ml", "cy", 
        "sk", "te", "fa", "lv", "bn", "sr", "az", "sl", "kn", "et", "mk", "br", "eu", 
        "is", "hy", "ne", "mn", "bs", "kk", "sq", "sw", "gl", "mr", "pa", "si", "km", 
        "sn", "yo", "so", "af", "oc", "ka", "be", "tg", "sd", "gu", "am", "yi", "lo", 
        "uz", "fo", "ht", "ps", "tk", "nn", "mt", "sa", "lb", "my", "bo", "tl", "mg", 
        "as", "tt", "haw", "ln", "ha", "ba", "jw", "su"
    };
    
    for (const char* lang : lang_codes) {
        languages.emplace_back(lang);
    }
    
    return languages;
#else
    return {};
#endif
}

bool Transcriber::is_available() {
#if V2S_HAVE_WHISPER
    return true;
#else
    return false;
#endif
}

std::string Transcriber::model_size_to_string(WhisperModelSize size) {
    switch (size) {
        case WhisperModelSize::TINY: return "tiny";
        case WhisperModelSize::BASE: return "base";
        case WhisperModelSize::SMALL: return "small";
        case WhisperModelSize::MEDIUM: return "medium";
        case WhisperModelSize::LARGE: return "large";
        default: return "base";
    }
}

std::optional<WhisperModelSize> Transcriber::string_to_model_size(const std::string& size_str) {
    std::string lower_size = size_str;
    std::transform(lower_size.begin(), lower_size.end(), lower_size.begin(), ::tolower);
    
    if (lower_size == "tiny") return WhisperModelSize::TINY;
    if (lower_size == "base") return WhisperModelSize::BASE;
    if (lower_size == "small") return WhisperModelSize::SMALL;
    if (lower_size == "medium") return WhisperModelSize::MEDIUM;
    if (lower_size == "large") return WhisperModelSize::LARGE;
    
    return std::nullopt;
}

void Transcriber::cleanup() {
#if V2S_HAVE_WHISPER
    if (ctx_) {
        whisper_free(ctx_);
        ctx_ = nullptr;
    }
#endif
    model_loaded_ = false;
}

std::filesystem::path Transcriber::get_model_file_path() const {
    if (!config_.model_path.empty()) {
        return config_.model_path;
    }
    
    // 使用统一的 ModelManager 管理模型目录与命名
    return ModelManager::get_model_file_path(model_size_to_string(config_.model_size));
}

std::vector<float> Transcriber::load_audio_data(const std::filesystem::path& audio_path) {
    // 这里简化实现，实际应该使用FFmpeg或其他音频库来加载WAV文件
    // 假设输入是16kHz单声道WAV文件
    
    std::ifstream file(audio_path, std::ios::binary);
    if (!file.is_open()) {
        throw std::runtime_error("无法打开音频文件: " + audio_path.string());
    }
    
    // 跳过WAV头部（简化处理，假设44字节头部）
    file.seekg(44);
    
    // 读取音频数据
    std::vector<int16_t> raw_data;
    int16_t sample;
    while (file.read(reinterpret_cast<char*>(&sample), sizeof(sample))) {
        raw_data.push_back(sample);
    }
    
    // 转换为float格式（归一化到[-1, 1]）
    std::vector<float> audio_data;
    audio_data.reserve(raw_data.size());
    
    for (int16_t sample : raw_data) {
        audio_data.push_back(static_cast<float>(sample) / 32768.0f);
    }
    
    return audio_data;
}

} // namespace v2s