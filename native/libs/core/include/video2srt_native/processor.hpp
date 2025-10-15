#pragma once

#include "models.hpp"
#include "audio.hpp"
#include "formatter.hpp"
#include "transcriber.hpp"
#include <string>
#include <memory>
#include <filesystem>
#include <functional>

namespace v2s {

/**
 * 处理进度回调函数类型
 * @param stage 当前阶段名称
 * @param progress 进度百分比 (0.0 - 1.0)
 * @param message 进度消息
 */
using ProgressCallback = std::function<void(const std::string& stage, double progress, const std::string& message)>;

/**
 * 核心处理器
 * 整合音频提取、转录、格式化的完整流水线
 */
class Processor {
public:
    /**
     * 构造函数
     * @param config 处理配置
     */
    explicit Processor(const ProcessingConfig& config = ProcessingConfig{});
    
    /**
     * 析构函数
     */
    ~Processor() = default;
    
    // 禁用拷贝构造和赋值
    Processor(const Processor&) = delete;
    Processor& operator=(const Processor&) = delete;
    
    // 支持移动构造和赋值
    Processor(Processor&&) = default;
    Processor& operator=(Processor&&) = default;
    
    /**
     * 处理视频/音频文件，生成SRT字幕
     * @param input_path 输入文件路径（视频或音频）
     * @param output_path 输出SRT文件路径
     * @param progress_callback 进度回调函数（可选）
     * @return 处理结果
     */
    ProcessingResult process(const std::filesystem::path& input_path,
                           const std::filesystem::path& output_path,
                           ProgressCallback progress_callback = nullptr);
    
    /**
     * 仅提取音频（不进行转录）
     * @param input_path 输入文件路径
     * @param output_path 输出WAV文件路径
     * @param progress_callback 进度回调函数（可选）
     * @return 是否成功
     */
    bool extract_audio_only(const std::filesystem::path& input_path,
                          const std::filesystem::path& output_path,
                          ProgressCallback progress_callback = nullptr);
    
    /**
     * 仅转录音频文件（假设已是WAV格式）
     * @param audio_path 音频文件路径
     * @param progress_callback 进度回调函数（可选）
     * @return 转录结果
     */
    TranscriptionResult transcribe_only(const std::filesystem::path& audio_path,
                                      ProgressCallback progress_callback = nullptr);
    
    /**
     * 设置处理配置
     * @param config 新的配置
     */
    void set_config(const ProcessingConfig& config);
    
    /**
     * 获取当前配置
     * @return 当前配置
     */
    const ProcessingConfig& get_config() const;
    
    /**
     * 检查系统能力
     * @return 系统能力信息
     */
    struct SystemCapabilities {
        bool has_ffmpeg = false;
        bool has_whisper = false;
        std::vector<std::string> supported_input_formats;
        std::vector<std::string> supported_languages;
    };
    
    static SystemCapabilities check_capabilities();
    
    /**
     * 获取支持的输入格式
     * @return 支持的文件扩展名列表
     */
    static std::vector<std::string> get_supported_formats();
    
    /**
     * 验证输入文件
     * @param input_path 输入文件路径
     * @return 是否为支持的格式
     */
    static bool is_supported_format(const std::filesystem::path& input_path);

private:
    ProcessingConfig config_;
    std::unique_ptr<Transcriber> transcriber_;
    
    /**
     * 初始化转录器
     * @return 是否成功
     */
    bool initialize_transcriber();
    
    /**
     * 创建临时目录
     * @return 临时目录路径
     */
    std::filesystem::path create_temp_directory();
    
    /**
     * 清理临时文件
     * @param temp_dir 临时目录路径
     */
    void cleanup_temp_files(const std::filesystem::path& temp_dir);
    
    /**
     * 报告进度
     * @param callback 回调函数
     * @param stage 阶段名称
     * @param progress 进度
     * @param message 消息
     */
    void report_progress(ProgressCallback callback, 
                        const std::string& stage, 
                        double progress, 
                        const std::string& message);
    
    /**
     * 验证配置
     * @return 是否有效
     */
    bool validate_config() const;
};

} // namespace v2s