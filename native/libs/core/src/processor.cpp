#include "video2srt_native/processor.hpp"
#include "video2srt_native/transcriber.hpp"
#include "video2srt_native/core.hpp"
#include "video2srt_native/translator.hpp"
#include "video2srt_native/output_formats.hpp"
#include <iostream>
#include <sstream>
#include <algorithm>
#include <random>

namespace v2s {

Processor::Processor(const ProcessingConfig& config)
    : config_(config), transcriber_(nullptr) {
}

ProcessingResult Processor::process(const std::filesystem::path& input_path,
                                  const std::filesystem::path& output_path,
                                  ProgressCallback progress_callback) {
    ProcessingResult result;
    result.success = false;
    
    try {
        // 验证输入
        if (!std::filesystem::exists(input_path)) {
            result.error_message = "输入文件不存在: " + input_path.string();
            return result;
        }
        
        if (!is_supported_format(input_path)) {
            result.error_message = "不支持的文件格式: " + input_path.extension().string();
            return result;
        }
        
        if (!validate_config()) {
            result.error_message = "配置验证失败";
            return result;
        }
        
        report_progress(progress_callback, "初始化", 0.0, "开始处理...");
        
        // 创建临时目录
        std::filesystem::path temp_dir = create_temp_directory();
        
        // 阶段1: 音频提取
        report_progress(progress_callback, "音频提取", 0.1, "正在提取音频...");
        
        std::filesystem::path audio_path = temp_dir / "extracted_audio.wav";
        
        if (!extract_audio_to_wav(input_path.string(), audio_path.string(), 16000)) {
            cleanup_temp_files(temp_dir);
            result.error_message = "音频提取失败";
            return result;
        }
        
        report_progress(progress_callback, "音频提取", 0.3, "音频提取完成");
        
        // 阶段2: 语音转录
        report_progress(progress_callback, "语音转录", 0.4, "正在加载转录模型...");
        
        if (!initialize_transcriber()) {
            cleanup_temp_files(temp_dir);
            result.error_message = "转录器初始化失败";
            return result;
        }
        
        report_progress(progress_callback, "语音转录", 0.5, "正在转录音频...");
        
        TranscriptionResult transcription = transcriber_->transcribe(audio_path, config_.language);
        
        report_progress(progress_callback, "语音转录", 0.8, "转录完成");
        
        // 阶段3: 合并与翻译
        report_progress(progress_callback, "处理字幕", 0.85, "正在整理字幕段...");

        // 应用段合并与限制
        std::vector<Segment> processed_segments = transcription.segments;
        if (config_.merge_segments) {
            processed_segments = merge_segments(processed_segments,
                                               config_.max_segment_duration,
                                               config_.max_segment_chars);
        }

        // 翻译（如果需要）
        std::optional<TranslationResult> translation_result;
        if (config_.translate_to.has_value()) {
            report_progress(progress_callback, "翻译", 0.9, "正在翻译字幕...");
            auto translator = create_translator(config_.translator_type, config_.translator_options);
            translation_result = translator->translate_segments(processed_segments,
                                                                config_.translate_to.value(),
                                                                transcription.language);
        }

        // 阶段4: 格式化与保存
        report_progress(progress_callback, "保存", 0.95, "正在生成输出文件...");

        bool save_ok = false;
        std::string fmt = config_.output_format;
        std::transform(fmt.begin(), fmt.end(), fmt.begin(), ::tolower);

        if (fmt == "vtt") {
            // 生成VTT内容
            std::string vtt_content;
            if (translation_result.has_value()) {
                if (config_.bilingual) {
                    vtt_content = WebVTTFormatter::create_bilingual_vtt(processed_segments, translation_result->segments);
                } else {
                    vtt_content = WebVTTFormatter::format_segments(translation_result->segments, config_.min_segment_duration);
                }
            } else {
                vtt_content = WebVTTFormatter::format_segments(processed_segments, config_.min_segment_duration);
            }
            save_ok = WebVTTFormatter::save_vtt(vtt_content, output_path);
            if (!save_ok) {
                cleanup_temp_files(temp_dir);
                result.error_message = "保存VTT文件失败: " + output_path.string();
                return result;
            }
        } else if (fmt == "ass") {
            // 生成ASS内容
            std::string ass_content;
            if (translation_result.has_value()) {
                if (config_.bilingual) {
                    ass_content = ASSFormatter::create_bilingual_ass(processed_segments, translation_result->segments, config_.ass_style, config_.min_segment_duration);
                } else {
                    ass_content = ASSFormatter::format_segments(translation_result->segments, config_.ass_style, config_.min_segment_duration);
                }
            } else {
                ass_content = ASSFormatter::format_segments(processed_segments, config_.ass_style, config_.min_segment_duration);
            }
            save_ok = ASSFormatter::save_ass(ass_content, output_path);
            if (!save_ok) {
                cleanup_temp_files(temp_dir);
                result.error_message = "保存ASS文件失败: " + output_path.string();
                return result;
            }
        } else { // 默认SRT
            std::string srt_content;
            if (translation_result.has_value()) {
                if (config_.bilingual) {
                    srt_content = SRTFormatter::create_bilingual_srt(processed_segments, translation_result->segments);
                } else {
                    srt_content = SRTFormatter::format_segments(translation_result->segments, config_.min_segment_duration);
                }
            } else {
                srt_content = SRTFormatter::format_segments(processed_segments, config_.min_segment_duration);
            }
            save_ok = SRTFormatter::save_srt(srt_content, output_path);
            if (!save_ok) {
                cleanup_temp_files(temp_dir);
                result.error_message = "保存SRT文件失败: " + output_path.string();
                return result;
            }
        }
        
        report_progress(progress_callback, "完成", 1.0, "处理完成");
        
        // 清理临时文件
        cleanup_temp_files(temp_dir);
        
        // 设置结果
        result.success = true;
        result.output_path = output_path.string();
        result.transcription = transcription;
        if (translation_result.has_value()) {
            result.translation = translation_result.value();
        }
        // result.segments = processed_segments;  // ProcessingResult没有segments字段
        result.processing_time = 0.0;  // TODO: 实际计算处理时间
        
    } catch (const std::exception& e) {
        result.error_message = "处理过程中发生错误: " + std::string(e.what());
    }
    
    return result;
}

bool Processor::extract_audio_only(const std::filesystem::path& input_path,
                                 const std::filesystem::path& output_path,
                                 ProgressCallback progress_callback) {
    try {
        if (!std::filesystem::exists(input_path)) {
            return false;
        }
        
        report_progress(progress_callback, "音频提取", 0.0, "开始提取音频...");
        
        bool success = extract_audio_to_wav(input_path.string(), output_path.string(), 16000);
        
        if (success) {
            report_progress(progress_callback, "音频提取", 1.0, "音频提取完成");
        } else {
            report_progress(progress_callback, "音频提取", 0.0, "音频提取失败");
        }
        
        return success;
    } catch (const std::exception&) {
        return false;
    }
}

TranscriptionResult Processor::transcribe_only(const std::filesystem::path& audio_path,
                                             ProgressCallback progress_callback) {
    TranscriptionResult result;
    
    try {
        if (!std::filesystem::exists(audio_path)) {
            throw std::runtime_error("音频文件不存在");
        }
        
        report_progress(progress_callback, "转录", 0.0, "初始化转录器...");
        
        if (!initialize_transcriber()) {
            throw std::runtime_error("转录器初始化失败");
        }
        
        report_progress(progress_callback, "转录", 0.2, "开始转录...");
        
        result = transcriber_->transcribe(audio_path, config_.language);
        
        report_progress(progress_callback, "转录", 1.0, "转录完成");
        
    } catch (const std::exception& e) {
        std::cerr << "转录失败: " << e.what() << std::endl;
        // 返回空结果，调用者可以检查segments是否为空
    }
    
    return result;
}

void Processor::set_config(const ProcessingConfig& config) {
    config_ = config;
    // 重置转录器以应用新配置
    transcriber_.reset();
}

const ProcessingConfig& Processor::get_config() const {
    return config_;
}

Processor::SystemCapabilities Processor::check_capabilities() {
    SystemCapabilities caps;
    
    caps.has_ffmpeg = has_ffmpeg();
    caps.has_whisper = Transcriber::is_available();
    
    if (caps.has_ffmpeg) {
        caps.supported_input_formats = get_supported_formats();
    }
    
    if (caps.has_whisper) {
        caps.supported_languages = Transcriber::get_supported_languages();
    }
    
    return caps;
}

std::vector<std::string> Processor::get_supported_formats() {
    // 常见的视频和音频格式
    return {
        ".mp4", ".avi", ".mkv", ".mov", ".wmv", ".flv", ".webm", ".m4v",
        ".mp3", ".wav", ".flac", ".aac", ".ogg", ".wma", ".m4a"
    };
}

bool Processor::is_supported_format(const std::filesystem::path& input_path) {
    std::string ext = input_path.extension().string();
    std::transform(ext.begin(), ext.end(), ext.begin(), ::tolower);
    
    auto supported = get_supported_formats();
    return std::find(supported.begin(), supported.end(), ext) != supported.end();
}

bool Processor::initialize_transcriber() {
    if (transcriber_ && transcriber_->is_model_loaded()) {
        return true;
    }
    
    try {
        TranscriptionConfig transcription_config;
        
        // 从处理配置映射到转录配置
        if (config_.model_size == "tiny") {
            transcription_config.model_size = WhisperModelSize::TINY;
        } else if (config_.model_size == "base") {
            transcription_config.model_size = WhisperModelSize::BASE;
        } else if (config_.model_size == "small") {
            transcription_config.model_size = WhisperModelSize::SMALL;
        } else if (config_.model_size == "medium") {
            transcription_config.model_size = WhisperModelSize::MEDIUM;
        } else if (config_.model_size == "large") {
            transcription_config.model_size = WhisperModelSize::LARGE;
        } else {
            transcription_config.model_size = WhisperModelSize::BASE;  // 默认
        }
        
        transcription_config.language = config_.language;
        // 性能与硬件设置
        transcription_config.use_gpu = config_.use_gpu || (config_.device == "cuda");
        transcription_config.n_threads = (config_.cpu_threads > 0) ? config_.cpu_threads : 4;
        transcription_config.verbose = false;  // 在处理器中控制输出
        
        transcriber_ = std::make_unique<Transcriber>(transcription_config);
        
        return transcriber_->load_model();
    } catch (const std::exception& e) {
        std::cerr << "转录器初始化失败: " << e.what() << std::endl;
        return false;
    }
}

std::filesystem::path Processor::create_temp_directory() {
    // 创建临时目录
    std::filesystem::path temp_base = std::filesystem::temp_directory_path();
    
    // 生成随机目录名
    std::random_device rd;
    std::mt19937 gen(rd());
    std::uniform_int_distribution<> dis(1000, 9999);
    
    std::string temp_name = "video2srt_" + std::to_string(dis(gen));
    std::filesystem::path temp_dir = temp_base / temp_name;
    
    std::filesystem::create_directories(temp_dir);
    
    return temp_dir;
}

void Processor::cleanup_temp_files(const std::filesystem::path& temp_dir) {
    try {
        if (std::filesystem::exists(temp_dir)) {
            std::filesystem::remove_all(temp_dir);
        }
    } catch (const std::exception& e) {
        std::cerr << "清理临时文件失败: " << e.what() << std::endl;
    }
}

void Processor::report_progress(ProgressCallback callback, 
                              const std::string& stage, 
                              double progress, 
                              const std::string& message) {
    if (callback) {
        callback(stage, progress, message);
    }
}

bool Processor::validate_config() const {
    // 基本验证
    if (config_.model_size.empty()) {
        return false;
    }
    // 性能参数验证
    if (config_.cpu_threads <= 0) {
        return false;
    }
    // 段时长与字符限制参数
    if (config_.max_segment_duration <= 0) {
        return false;
    }
    if (config_.min_segment_duration < 0) {
        return false;
    }
    if (config_.max_segment_chars == 0) {
        return false;
    }
    // 输出格式
    std::string fmt = config_.output_format;
    std::transform(fmt.begin(), fmt.end(), fmt.begin(), ::tolower);
    if (!(fmt == "srt" || fmt == "vtt" || fmt == "ass")) {
        return false;
    }
    // 设备设置
    if (!(config_.device == "auto" || config_.device == "cpu" || config_.device == "cuda")) {
        return false;
    }
    return true;
}

} // namespace v2s