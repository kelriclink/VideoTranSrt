#pragma once

#include <string>
#include <vector>
#include <optional>
#include <chrono>

namespace v2s {

/**
 * 字幕段数据结构
 * 对应Python版本的Segment类
 */
struct Segment {
    double start;                           // 开始时间（秒）
    double end;                            // 结束时间（秒）
    std::string text;                      // 文本内容
    std::optional<std::string> language;   // 语言代码
    std::optional<double> confidence;      // 置信度 [0.0, 1.0]
    
    Segment() = default;
    
    Segment(double start_time, double end_time, const std::string& content)
        : start(start_time), end(end_time), text(content) {}
    
    Segment(double start_time, double end_time, const std::string& content, 
            const std::string& lang, double conf = -1.0)
        : start(start_time), end(end_time), text(content), language(lang) {
        if (conf >= 0.0) {
            confidence = conf;
        }
    }
    
    // 获取时长
    double duration() const {
        return end - start;
    }
    
    // 验证数据有效性
    bool is_valid() const {
        return start >= 0.0 && end > start && !text.empty();
    }
};

/**
 * 转录结果数据结构
 * 对应Python版本的TranscriptionResult类
 */
struct TranscriptionResult {
    std::vector<Segment> segments;         // 字幕段列表
    std::string language;                  // 检测到的语言
    std::string text;                      // 完整文本
    double duration;                       // 总时长（秒）
    std::string model_name;                // 使用的模型名称
    
    TranscriptionResult() = default;
    
    TranscriptionResult(const std::vector<Segment>& segs, const std::string& lang, 
                       const std::string& full_text, const std::string& model)
        : segments(segs), language(lang), text(full_text), model_name(model) {
        // 计算总时长
        if (!segments.empty()) {
            duration = segments.back().end;
        } else {
            duration = 0.0;
        }
    }
    
    // 获取段数
    size_t segment_count() const {
        return segments.size();
    }
    
    // 验证结果有效性
    bool is_valid() const {
        return !language.empty() && !model_name.empty();
    }
};

/**
 * 翻译结果数据结构
 * 对应Python版本的TranslationResult类
 */
struct TranslationResult {
    std::vector<Segment> segments;         // 翻译后的字幕段
    std::string source_language;          // 源语言
    std::string target_language;          // 目标语言
    std::string translator_name;          // 翻译器名称
    
    TranslationResult() = default;
    
    TranslationResult(const std::vector<Segment>& segs, const std::string& src_lang,
                     const std::string& tgt_lang, const std::string& translator)
        : segments(segs), source_language(src_lang), target_language(tgt_lang), translator_name(translator) {}
    
    // 获取段数
    size_t segment_count() const {
        return segments.size();
    }
    
    // 验证结果有效性
    bool is_valid() const {
        return !source_language.empty() && !target_language.empty() && !translator_name.empty();
    }
};

/**
 * 翻译器选项（来自配置文件或CLI）
 */
struct TranslatorOptions {
    int timeout_seconds = 15;            // 请求超时
    int retry_count = 3;                 // 重试次数
    bool ssl_bypass = false;             // 是否忽略SSL证书错误（仅Windows WinHTTP）
    std::string api_key;                 // API密钥（OpenAI等）
    std::string base_url;                // 基础URL（OpenAI/自建网关）
    std::string model;                   // 模型名称（OpenAI）
    int max_tokens = 4000;               // 最大tokens（OpenAI）
    double temperature = 0.3;            // 采样温度（OpenAI）
};

/**
 * ASS字幕样式配置
 */
struct ASSStyleConfig {
    std::string style_name = "Default"; // 样式名称
    std::string font_name = "Arial";    // 字体名称
    int font_size = 36;                  // 字体大小
    std::string primary_color = "&H00FFFFFF"; // 主颜色（ASS格式）
    int outline = 2;                     // 描边宽度
    int shadow = 0;                      // 阴影大小
    int alignment = 2;                   // 对齐（1-9，2为底部居中）
};

/**
 * 处理配置数据结构
 * 对应Python版本的ProcessingConfig类
 */
struct ProcessingConfig {
    std::string input_path;                // 输入文件路径
    std::string output_path;               // 输出文件路径（可选）
    std::string model_size = "base";       // 模型大小
    std::optional<std::string> language;   // 源语言（None表示自动检测）
    std::optional<std::string> translate_to; // 目标语言（None表示不翻译）
    bool bilingual = false;                // 是否生成双语字幕
    std::string translator_type = "simple"; // 翻译器类型（默认simple，避免外部依赖）
    std::string device = "auto";           // 设备类型 (cpu, cuda, auto)
    TranslatorOptions translator_options;   // 翻译器选项

    // 片段合并与格式控制
    bool merge_segments = false;           // 是否合并短片段
    double min_segment_duration = 1.0;     // 最短片段时长（秒）
    double max_segment_duration = 30.0;    // 最长片段时长（秒）
    size_t max_segment_chars = 500;        // 单片段最大字符数

    // 性能与硬件选项
    int cpu_threads = 4;                   // CPU线程数
    bool use_gpu = false;                  // 是否启用GPU（如果可用）

    // 输出格式
    std::string output_format = "srt";     // 输出格式：srt/vtt/ass
    ASSStyleConfig ass_style;               // ASS样式配置
    
    ProcessingConfig() = default;
    
    ProcessingConfig(const std::string& input) : input_path(input) {
        // 如果没有指定输出路径，自动生成
        if (output_path.empty()) {
            size_t dot_pos = input_path.find_last_of('.');
            if (dot_pos != std::string::npos) {
                output_path = input_path.substr(0, dot_pos) + ".srt";
            } else {
                output_path = input_path + ".srt";
            }
        }
    }
    
    // 验证配置有效性
    bool is_valid() const {
        return !input_path.empty() && !output_path.empty() && !model_size.empty();
    }
};

/**
 * 处理结果数据结构
 * 对应Python版本的ProcessingResult类
 */
struct ProcessingResult {
    bool success = false;                           // 是否成功
    std::string output_path;                        // 输出文件路径
    std::optional<TranscriptionResult> transcription; // 转录结果
    std::optional<TranslationResult> translation;   // 翻译结果
    std::string error_message;                      // 错误信息
    std::optional<double> processing_time;          // 处理耗时（秒）
    
    ProcessingResult() = default;
    
    // 成功结果构造函数
    ProcessingResult(const std::string& output, const TranscriptionResult& trans_result)
        : success(true), output_path(output), transcription(trans_result) {}
    
    // 失败结果构造函数
    ProcessingResult(const std::string& error) : success(false), error_message(error) {}
    
    // 设置处理时间
    void set_processing_time(const std::chrono::steady_clock::time_point& start_time) {
        auto end_time = std::chrono::steady_clock::now();
        auto duration = std::chrono::duration_cast<std::chrono::milliseconds>(end_time - start_time);
        processing_time = duration.count() / 1000.0;
    }
};

/**
 * 模型信息数据结构
 * 对应Python版本的ModelInfo类
 */
struct ModelInfo {
    std::string name;                      // 模型名称
    std::string size;                      // 模型大小 (tiny, base, small, medium, large)
    std::string type;                      // 模型类型 (multilingual, english, turbo)
    std::optional<size_t> file_size;       // 文件大小（字节）
    bool is_downloaded = false;            // 是否已下载
    std::optional<std::string> download_url; // 下载URL
    
    ModelInfo() = default;
    
    ModelInfo(const std::string& model_name, const std::string& model_size, const std::string& model_type)
        : name(model_name), size(model_size), type(model_type) {}
    
    // 获取显示名称
    std::string display_name() const {
        if (type == "english") {
            return size + ".en";
        } else if (type == "turbo") {
            return size + "-turbo";
        } else {
            return size;
        }
    }
    
    // 获取文件大小（MB）
    std::optional<double> file_size_mb() const {
        if (file_size.has_value()) {
            return file_size.value() / (1024.0 * 1024.0);
        }
        return std::nullopt;
    }
};

// 工具函数声明

/**
 * 合并短字幕段
 * @param segments 原始字幕段列表
 * @param max_duration 最大合并时长（秒）
 * @param max_chars 最大字符数
 * @return 合并后的字幕段列表
 */
std::vector<Segment> merge_segments(const std::vector<Segment>& segments, 
                                   double max_duration = 10.0, 
                                   size_t max_chars = 200);

/**
 * 验证字幕段列表的有效性
 * @param segments 字幕段列表
 * @return 是否有效
 */
bool validate_segments(const std::vector<Segment>& segments);

/**
 * 格式化时间为SRT格式 (HH:MM:SS,mmm)
 * @param seconds 时间（秒）
 * @return SRT格式时间字符串
 */
std::string format_srt_time(double seconds);

} // namespace v2s