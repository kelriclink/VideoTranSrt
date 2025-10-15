#include <iostream>
#include <string>
#include <filesystem>
#include <iomanip>
#include <chrono>
#ifdef _WIN32
#include <windows.h>
#endif
#include "video2srt_native/processor.hpp"
#include "video2srt_native/core.hpp"
#include "video2srt_native/config_manager.hpp"
#include "video2srt_native/model_manager.hpp"

static void print_usage() {
    std::cout << "Video2SRT Native CLI " << v2s::version() << "\n";
    std::cout << "将视频/音频文件转换为SRT字幕文件\n\n";
    std::cout << "用法:\n";
    std::cout << "  v2s_cli <input_file> [options]\n\n";
    std::cout << "选项:\n";
    std::cout << "  -o, --output <file>     输出字幕文件路径 (默认: 与输入文件同名.扩展名)\n";
    std::cout << "  -l, --language <lang>   指定语言 (默认: auto)\n";
    std::cout << "  -m, --model <size>      模型大小 (tiny/base/small/medium/large, 默认: base)\n";
    std::cout << "  --gpu                   使用GPU加速 (如果可用)\n";
    std::cout << "  --threads <n>           CPU线程数 (默认: 4)\n";
    std::cout << "  --merge                 合并短段落\n";
    std::cout << "  --min-duration <sec>    最小段落时长 (默认: 1.0)\n";
    std::cout << "  --max-duration <sec>    最大段落时长 (默认: 30.0)\n";
    std::cout << "  --max-chars <n>         最大字符数 (默认: 500)\n";
    std::cout << "  --format <fmt>          输出格式: srt / vtt / ass (默认: srt)\n";
    std::cout << "  --translate <lang>      目标语言代码 (例如: zh, en)，未设置则不翻译\n";
    std::cout << "  --translator <type>     翻译器类型: simple / google / openai / offline\n";
    std::cout << "  --timeout <sec>         翻译请求超时（秒），覆盖默认配置\n";
    std::cout << "  --retry <n>             翻译失败重试次数，覆盖默认配置\n";
    std::cout << "  --ssl-bypass            (Windows) 忽略SSL证书错误（WinHTTP，谨慎使用）\n";
    std::cout << "  --ass-style-name <s>    ASS样式名称 (默认: Default)\n";
    std::cout << "  --ass-font-name <s>     ASS字体名称 (默认: Arial)\n";
    std::cout << "  --ass-font-size <n>     ASS字体大小 (默认: 36)\n";
    std::cout << "  --ass-color <ASS>       ASS主颜色 (例如: &H00FFFFFF)\n";
    std::cout << "  --ass-outline <n>       ASS描边宽度 (默认: 2)\n";
    std::cout << "  --ass-shadow <n>        ASS阴影大小 (默认: 0)\n";
    std::cout << "  --ass-alignment <n>     ASS对齐 (1-9，2为底部居中)\n";
    std::cout << "  --bilingual             生成双语字幕 (原文+译文)\n";
    std::cout << "  --audio-only            仅提取音频 (输出WAV文件)\n";
    std::cout << "  --check                 检查系统能力\n";
    std::cout << "\n模型管理:\n";
    std::cout << "  --list-models           列出支持的模型及下载状态\n";
    std::cout << "  --download-model <size> 下载指定模型 (tiny/base/small/medium/large)\n";
    std::cout << "  --delete-model <size>   删除指定模型文件\n";
    std::cout << "  --model-dir <path>      指定模型目录 (默认: 当前目录的 models/)\n";
    std::cout << "  -h, --help              显示此帮助信息\n\n";
    std::cout << "示例:\n";
    std::cout << "  v2s_cli video.mp4\n";
    std::cout << "  v2s_cli video.mp4 -o subtitles.srt -l zh --gpu\n";
    std::cout << "  v2s_cli audio.wav --model small --merge\n";
    std::cout << "  v2s_cli video.mp4 --format vtt --translate zh --bilingual\n";
    std::cout << "  v2s_cli video.mp4 --format ass --translate en --translator google\n";
    std::cout << "  v2s_cli video.mp4 --audio-only -o audio.wav\n";
}

static void print_capabilities() {
    std::cout << "系统能力检查:\n";
    
    v2s::Processor processor(v2s::ProcessingConfig{});
    auto caps = processor.check_capabilities();
    
    std::cout << "FFmpeg支持: " << (caps.has_ffmpeg ? "✓" : "✗") << "\n";
    std::cout << "Whisper支持: " << (caps.has_whisper ? "✓" : "✗") << "\n";
    
    if (caps.has_ffmpeg && !caps.supported_input_formats.empty()) {
        std::cout << "支持的输入格式: ";
        for (size_t i = 0; i < caps.supported_input_formats.size(); ++i) {
            std::cout << caps.supported_input_formats[i];
            if (i < caps.supported_input_formats.size() - 1) std::cout << ", ";
        }
        std::cout << "\n";
    }
    
    if (caps.has_whisper && !caps.supported_languages.empty()) {
        std::cout << "支持的语言: ";
        for (size_t i = 0; i < caps.supported_languages.size() && i < 10; ++i) {
            std::cout << caps.supported_languages[i];
            if (i < std::min(caps.supported_languages.size() - 1, size_t(9))) std::cout << ", ";
        }
        if (caps.supported_languages.size() > 10) {
            std::cout << "... (共" << caps.supported_languages.size() << "种)";
        }
        std::cout << "\n";
    }
}

static void progress_callback(const std::string& stage, double progress, const std::string& message) {
    // 创建进度条
    int bar_width = 40;
    int pos = static_cast<int>(bar_width * progress);
    
    std::cout << "\r[" << stage << "] ";
    std::cout << "[";
    for (int i = 0; i < bar_width; ++i) {
        if (i < pos) std::cout << "=";
        else if (i == pos) std::cout << ">";
        else std::cout << " ";
    }
    std::cout << "] " << std::fixed << std::setprecision(1) << (progress * 100.0) << "% ";
    std::cout << message;
    std::cout.flush();
    
    if (progress >= 1.0) {
        std::cout << "\n";
    }
}

static std::string generate_output_path(const std::string& input_path, bool audio_only = false, const std::string& fmt = "srt") {
    std::filesystem::path input(input_path);
    std::filesystem::path output = input.parent_path() / input.stem();
    
    if (audio_only) {
        output += ".wav";
    } else {
        if (fmt == "vtt") {
            output += ".vtt";
        } else if (fmt == "ass") {
            output += ".ass";
        } else {
            output += ".srt";
        }
    }
    
    return output.string();
}

int main(int argc, char** argv) {
#ifdef _WIN32
    // 设置 Windows 控制台为 UTF-8，避免中文输出乱码
    SetConsoleOutputCP(CP_UTF8);
    SetConsoleCP(CP_UTF8);
#endif
    if (argc < 2) {
        print_usage();
        return 0;
    }
    
    // 解析命令行参数
    std::string input_file;
    std::string output_file;
    std::string language = "auto";
    std::string model_size = "base";
    bool use_gpu = false;
    int threads = 4;
    bool merge_segments = false;
    double min_duration = 1.0;
    double max_duration = 30.0;
    int max_chars = 500;
    bool audio_only = false;
    bool check_caps = false;
    std::string output_format = "srt";
    std::string translate_to;
    bool bilingual = false;
    std::string translator_type;
    int translator_timeout = -1;
    int translator_retry = -1;
    bool translator_ssl_bypass = false;
    bool ssl_bypass_set = false;
    // ASS 样式选项
    std::string ass_style_name;
    std::string ass_font_name;
    int ass_font_size = -1;
    std::string ass_color;
    int ass_outline = -1;
    int ass_shadow = -1;
    int ass_alignment = -1;
    // 模型管理选项
    bool list_models = false;
    std::string download_model_size;
    std::string delete_model_size;
    std::string model_dir;
    
    for (int i = 1; i < argc; ++i) {
        std::string arg = argv[i];
        
        if (arg == "-h" || arg == "--help") {
            print_usage();
            return 0;
        } else if (arg == "--check") {
            check_caps = true;
        } else if (arg == "-o" || arg == "--output") {
            if (i + 1 < argc) {
                output_file = argv[++i];
            } else {
                std::cerr << "错误: " << arg << " 需要参数\n";
                return 1;
            }
        } else if (arg == "-l" || arg == "--language") {
            if (i + 1 < argc) {
                language = argv[++i];
            } else {
                std::cerr << "错误: " << arg << " 需要参数\n";
                return 1;
            }
        } else if (arg == "-m" || arg == "--model") {
            if (i + 1 < argc) {
                model_size = argv[++i];
            } else {
                std::cerr << "错误: " << arg << " 需要参数\n";
                return 1;
            }
        } else if (arg == "--gpu") {
            use_gpu = true;
        } else if (arg == "--threads") {
            if (i + 1 < argc) {
                threads = std::stoi(argv[++i]);
            } else {
                std::cerr << "错误: " << arg << " 需要参数\n";
                return 1;
            }
        } else if (arg == "--merge") {
            merge_segments = true;
        } else if (arg == "--min-duration") {
            if (i + 1 < argc) {
                min_duration = std::stod(argv[++i]);
            } else {
                std::cerr << "错误: " << arg << " 需要参数\n";
                return 1;
            }
        } else if (arg == "--max-duration") {
            if (i + 1 < argc) {
                max_duration = std::stod(argv[++i]);
            } else {
                std::cerr << "错误: " << arg << " 需要参数\n";
                return 1;
            }
        } else if (arg == "--max-chars") {
            if (i + 1 < argc) {
                max_chars = std::stoi(argv[++i]);
            } else {
                std::cerr << "错误: " << arg << " 需要参数\n";
                return 1;
            }
        } else if (arg == "--audio-only") {
            audio_only = true;
        } else if (arg == "--format") {
            if (i + 1 < argc) {
                output_format = argv[++i];
            } else {
                std::cerr << "错误: " << arg << " 需要参数\n";
                return 1;
            }
        } else if (arg == "--translator") {
            if (i + 1 < argc) {
                translator_type = argv[++i];
            } else {
                std::cerr << "错误: " << arg << " 需要参数\n";
                return 1;
            }
        } else if (arg == "--timeout") {
            if (i + 1 < argc) {
                translator_timeout = std::stoi(argv[++i]);
            } else {
                std::cerr << "错误: " << arg << " 需要参数\n";
                return 1;
            }
        } else if (arg == "--retry") {
            if (i + 1 < argc) {
                translator_retry = std::stoi(argv[++i]);
            } else {
                std::cerr << "错误: " << arg << " 需要参数\n";
                return 1;
            }
        } else if (arg == "--ssl-bypass") {
            translator_ssl_bypass = true;
            ssl_bypass_set = true;
        } else if (arg == "--translate") {
            if (i + 1 < argc) {
                translate_to = argv[++i];
            } else {
                std::cerr << "错误: " << arg << " 需要参数\n";
                return 1;
            }
        } else if (arg == "--ass-style-name") {
            if (i + 1 < argc) {
                ass_style_name = argv[++i];
            } else {
                std::cerr << "错误: " << arg << " 需要参数\n";
                return 1;
            }
        } else if (arg == "--ass-font-name") {
            if (i + 1 < argc) {
                ass_font_name = argv[++i];
            } else {
                std::cerr << "错误: " << arg << " 需要参数\n";
                return 1;
            }
        } else if (arg == "--ass-font-size") {
            if (i + 1 < argc) {
                ass_font_size = std::stoi(argv[++i]);
            } else {
                std::cerr << "错误: " << arg << " 需要参数\n";
                return 1;
            }
        } else if (arg == "--ass-color") {
            if (i + 1 < argc) {
                ass_color = argv[++i];
            } else {
                std::cerr << "错误: " << arg << " 需要参数\n";
                return 1;
            }
        } else if (arg == "--ass-outline") {
            if (i + 1 < argc) {
                ass_outline = std::stoi(argv[++i]);
            } else {
                std::cerr << "错误: " << arg << " 需要参数\n";
                return 1;
            }
        } else if (arg == "--ass-shadow") {
            if (i + 1 < argc) {
                ass_shadow = std::stoi(argv[++i]);
            } else {
                std::cerr << "错误: " << arg << " 需要参数\n";
                return 1;
            }
        } else if (arg == "--ass-alignment") {
            if (i + 1 < argc) {
                ass_alignment = std::stoi(argv[++i]);
            } else {
                std::cerr << "错误: " << arg << " 需要参数\n";
                return 1;
            }
        } else if (arg == "--bilingual") {
            bilingual = true;
        } else if (arg == "--list-models") {
            list_models = true;
        } else if (arg == "--download-model") {
            if (i + 1 < argc) {
                download_model_size = argv[++i];
            } else {
                std::cerr << "错误: " << arg << " 需要参数\n";
                return 1;
            }
        } else if (arg == "--delete-model") {
            if (i + 1 < argc) {
                delete_model_size = argv[++i];
            } else {
                std::cerr << "错误: " << arg << " 需要参数\n";
                return 1;
            }
        } else if (arg == "--model-dir") {
            if (i + 1 < argc) {
                model_dir = argv[++i];
            } else {
                std::cerr << "错误: " << arg << " 需要参数\n";
                return 1;
            }
        } else if (arg[0] != '-') {
            if (input_file.empty()) {
                input_file = arg;
            } else {
                std::cerr << "错误: 多个输入文件\n";
                return 1;
            }
        } else {
            std::cerr << "错误: 未知选项 " << arg << "\n";
            return 1;
        }
    }
    
    if (check_caps) {
        print_capabilities();
        return 0;
    }
    // 先应用配置文件的模型目录（如有），确保后续所有模型管理操作使用统一目录
    v2s::ConfigManager::apply_model_dir_from_config(std::filesystem::path("config/config.json"), std::filesystem::path("config/default_config.json"));
    // 应用模型目录（若指定）
    if (!model_dir.empty()) {
        v2s::ModelManager::set_model_dir(model_dir);
        std::cout << "模型目录: " << v2s::ModelManager::get_model_dir().string() << "\n";
    }

    // 若存在模型管理操作，优先执行并退出
    bool performed_model_ops = false;
    if (list_models) {
        auto infos = v2s::ModelManager::list_models();
        std::cout << "可用模型列表 (目录: " << v2s::ModelManager::get_model_dir().string() << ")\n";
        for (const auto& info : infos) {
            std::cout << "- " << info.size << "\t" << (info.is_downloaded ? "已下载" : "未下载");
            if (info.is_downloaded) {
                auto path = v2s::ModelManager::get_model_file_path(info.size);
                std::cout << " (" << path.string() << ", ";
                if (info.file_size.has_value()) {
                    std::cout << info.file_size.value() << " bytes)";
                } else {
                    std::cout << "未知大小)";
                }
            }
            std::cout << "\n";
        }
        performed_model_ops = true;
    }
    if (!download_model_size.empty()) {
        std::cout << "下载模型: " << download_model_size << "\n";
        bool ok = v2s::ModelManager::download_model(download_model_size, [](const std::string& name, size_t done, size_t total){
            double prog = total > 0 ? (double)done / (double)total : 0.0;
            int pct = (int)(prog * 100.0);
            std::cout << "\r[" << name << "] 已下载: " << done << "/" << total << " (" << pct << "%)";
            std::cout.flush();
        });
        std::cout << "\n";
        std::cout << (ok ? "下载完成" : "下载失败") << "\n";
        performed_model_ops = true;
    }
    if (!delete_model_size.empty()) {
        std::cout << "删除模型: " << delete_model_size << "\n";
        bool ok = v2s::ModelManager::delete_model(delete_model_size);
        std::cout << (ok ? "删除完成" : "删除失败或文件不存在") << "\n";
        performed_model_ops = true;
    }

    if (performed_model_ops && input_file.empty()) {
        return 0;
    }

    if (input_file.empty()) {
        std::cerr << "错误: 未指定输入文件\n";
        print_usage();
        return 1;
    }
    
    // 生成输出文件路径
    if (output_file.empty()) {
        output_file = generate_output_path(input_file, audio_only, output_format);
    }
    
    // 创建处理配置
    v2s::ProcessingConfig config;
    if (language != "auto" && !language.empty()) {
        config.language = language;
    } else {
        config.language = std::nullopt;
    }
    if (!translate_to.empty()) {
        config.translate_to = translate_to;
    }
    config.bilingual = bilingual;
    config.model_size = model_size;
    config.use_gpu = use_gpu;
    config.cpu_threads = threads;
    config.merge_segments = merge_segments;
    config.min_segment_duration = min_duration;
    config.max_segment_duration = max_duration;
    config.max_segment_chars = static_cast<size_t>(max_chars);
    config.output_format = output_format;
    if (!translator_type.empty()) {
        config.translator_type = translator_type;
    }

    // 优先应用用户配置（config/config.json），若不存在则回退到默认配置（config/default_config.json）
    if (!v2s::ConfigManager::apply_default_config(config, std::filesystem::path("config/config.json"))) {
        v2s::ConfigManager::apply_default_config(config);
    }

    // 覆盖翻译器选项（CLI优先）
    if (translator_timeout >= 0) {
        config.translator_options.timeout_seconds = translator_timeout;
    }
    if (translator_retry >= 0) {
        config.translator_options.retry_count = translator_retry;
    }
    if (ssl_bypass_set) {
        config.translator_options.ssl_bypass = translator_ssl_bypass;
    }
    // 应用ASS样式覆盖
    if (!ass_style_name.empty()) {
        config.ass_style.style_name = ass_style_name;
    }
    if (!ass_font_name.empty()) {
        config.ass_style.font_name = ass_font_name;
    }
    if (ass_font_size > 0) {
        config.ass_style.font_size = ass_font_size;
    }
    if (!ass_color.empty()) {
        config.ass_style.primary_color = ass_color;
    }
    if (ass_outline >= 0) {
        config.ass_style.outline = ass_outline;
    }
    if (ass_shadow >= 0) {
        config.ass_style.shadow = ass_shadow;
    }
    if (ass_alignment >= 0) {
        config.ass_style.alignment = ass_alignment;
    }
    
    // 创建处理器
    v2s::Processor processor(config);
    
    std::cout << "Video2SRT Native CLI " << v2s::version() << "\n";
    std::cout << "输入文件: " << input_file << "\n";
    std::cout << "输出文件: " << output_file << "\n";
    
    if (audio_only) {
        std::cout << "模式: 仅提取音频\n\n";
        
        auto start_time = std::chrono::high_resolution_clock::now();
        
        bool success = processor.extract_audio_only(input_file, output_file, progress_callback);
        
        auto end_time = std::chrono::high_resolution_clock::now();
        auto duration = std::chrono::duration_cast<std::chrono::seconds>(end_time - start_time);
        
        if (success) {
            std::cout << "音频提取完成! 耗时: " << duration.count() << "秒\n";
            return 0;
        } else {
            std::cerr << "音频提取失败!\n";
            return 2;
        }
    } else {
        std::cout << "模式: 视频转字幕\n";
        std::cout << "语言: " << language << "\n";
        std::cout << "模型: " << model_size << "\n";
        std::cout << "GPU加速: " << (use_gpu ? "是" : "否") << "\n";
        std::cout << "输出格式: " << output_format << "\n";
        if (!config.translator_type.empty()) {
            std::cout << "翻译器: " << config.translator_type << "\n";
        }
        if (output_format == std::string("ass")) {
            std::cout << "ASS样式: name=" << config.ass_style.style_name
                      << ", font=" << config.ass_style.font_name
                      << ", size=" << config.ass_style.font_size
                      << ", color=" << config.ass_style.primary_color
                      << ", outline=" << config.ass_style.outline
                      << ", shadow=" << config.ass_style.shadow
                      << ", align=" << config.ass_style.alignment << "\n";
        }
        if (!translate_to.empty()) {
            std::cout << "翻译到: " << translate_to << (bilingual ? " (双语)" : "") << "\n";
        }
        std::cout << "\n";
        
        auto start_time = std::chrono::high_resolution_clock::now();
        
        v2s::ProcessingResult result = processor.process(input_file, output_file, progress_callback);
        
        auto end_time = std::chrono::high_resolution_clock::now();
        auto duration = std::chrono::duration_cast<std::chrono::seconds>(end_time - start_time);
        
        if (result.success) {
            std::cout << "\n转换完成!\n";
            std::cout << "输出文件: " << result.output_path << "\n";
            if (result.transcription.has_value()) {
                std::cout << "检测语言: " << result.transcription->language << "\n";
                std::cout << "段落数量: " << result.transcription->segments.size() << "\n";
            }
            std::cout << "总耗时: " << duration.count() << "秒\n";
            return 0;
        } else {
            std::cerr << "\n转换失败: " << result.error_message << "\n";
            return 2;
        }
    }
}