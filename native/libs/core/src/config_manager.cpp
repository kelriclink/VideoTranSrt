#include "video2srt_native/config_manager.hpp"
#include "video2srt_native/model_manager.hpp"
#include <fstream>
#include <sstream>
#include <regex>

namespace v2s {

std::string ConfigManager::read_file(const std::filesystem::path& path) {
    std::ifstream f(path, std::ios::in);
    if (!f.is_open()) return {};
    std::ostringstream ss;
    ss << f.rdbuf();
    return ss.str();
}

// 简单的键值提取（不支持完整JSON，仅用于当前配置字段）
static bool extract_value_by_regex(const std::string& content, const std::string& key_regex, std::string& captured) {
    std::regex re(key_regex, std::regex::icase | std::regex::multiline);
    std::smatch m;
    if (std::regex_search(content, m, re) && m.size() > 1) {
        captured = m[1].str();
        return true;
    }
    return false;
}

bool ConfigManager::extract_bool(const std::string& content, const std::string& key, bool& out) {
    std::string captured;
    // 匹配 true/false
    std::string re = key + R"(\s*:\s*(true|false))";
    if (!extract_value_by_regex(content, re, captured)) return false;
    out = (captured == "true" || captured == "True" || captured == "TRUE");
    return true;
}

bool ConfigManager::extract_int(const std::string& content, const std::string& key, int& out) {
    std::string captured;
    std::string re = key + R"(\s*:\s*(-?\d+))";
    if (!extract_value_by_regex(content, re, captured)) return false;
    try { out = std::stoi(captured); return true; } catch (...) { return false; }
}

bool ConfigManager::extract_double(const std::string& content, const std::string& key, double& out) {
    std::string captured;
    std::string re = key + R"(\s*:\s*(-?\d+(?:\.\d+)?))";
    if (!extract_value_by_regex(content, re, captured)) return false;
    try { out = std::stod(captured); return true; } catch (...) { return false; }
}

bool ConfigManager::extract_string(const std::string& content, const std::string& key, std::string& out) {
    std::string captured;
    std::string re = key + R"(\s*:\s*\"([^\"]*)\")";
    if (!extract_value_by_regex(content, re, captured)) return false;
    out = captured;
    return true;
}

bool ConfigManager::apply_default_config(ProcessingConfig& config,
                                         const std::filesystem::path& config_path) {
    // 读取文件
    std::string content = read_file(config_path);
    if (content.empty()) {
        return false;
    }

    // general.default_translator
    std::string default_translator;
    if (extract_string(content, R"(\"default_translator\")", default_translator)) {
        // 仅在未显式设置或为默认simple时应用
        if (config.translator_type == "simple" || config.translator_type.empty()) {
            config.translator_type = default_translator;
        }
    }

    // whisper.model_size
    std::string whisper_model_size;
    if (extract_string(content, R"(\"model_size\")", whisper_model_size)) {
        if (config.model_size == "base") {
            config.model_size = whisper_model_size;
        }
    }

    // whisper.language
    std::string whisper_language;
    if (extract_string(content, R"(\"language\")", whisper_language)) {
        if (!config.language.has_value() || config.language->empty()) {
            if (whisper_language != "auto") {
                config.language = whisper_language;
            }
        }
    }

    // whisper.model_dir -> ModelManager::set_model_dir
    std::string whisper_model_dir;
    if (extract_string(content, R"(\"model_dir\")", whisper_model_dir)) {
        if (!whisper_model_dir.empty()) {
            // 使用更通用的分隔符写法
            std::filesystem::path dir(whisper_model_dir);
            v2s::ModelManager::set_model_dir(dir);
        }
    }

    // whisper.device -> use_gpu
    std::string whisper_device;
    if (extract_string(content, R"(\"device\")", whisper_device)) {
        if (whisper_device == "cuda" || whisper_device == "gpu") {
            config.use_gpu = true;
            config.device = "cuda";
        } else if (whisper_device == "cpu") {
            config.use_gpu = false;
            config.device = "cpu";
        }
    }

    // translators.google.*
    bool google_enabled = false;
    extract_bool(content, R"(\"google\"[\s\S]*?\"enabled\")", google_enabled);
    if (config.translator_type == "google" && google_enabled) {
        int timeout = 0, retry = 0; bool bypass = false;
        if (extract_int(content, R"(\"google\"[\s\S]*?\"timeout\")", timeout)) {
            config.translator_options.timeout_seconds = timeout;
        }
        if (extract_int(content, R"(\"google\"[\s\S]*?\"retry_count\")", retry)) {
            config.translator_options.retry_count = retry;
        }
        if (extract_bool(content, R"(\"google\"[\s\S]*?\"use_ssl_bypass\")", bypass)) {
            config.translator_options.ssl_bypass = bypass;
        }
        // 默认 base_url（注：非官方端点）
        config.translator_options.base_url = "https://translate.googleapis.com";
    }

    // translators.openai.*
    bool openai_enabled = false;
    extract_bool(content, R"(\"openai\"[\s\S]*?\"enabled\")", openai_enabled);
    if (config.translator_type == "openai" && openai_enabled) {
        std::string api_key, base_url, model; int max_tokens = 0; double temperature = 0.0; int timeout = 0; int retry = 0;
        if (extract_string(content, R"(\"openai\"[\s\S]*?\"api_key\")", api_key)) {
            config.translator_options.api_key = api_key;
        }
        if (extract_string(content, R"(\"openai\"[\s\S]*?\"base_url\")", base_url)) {
            config.translator_options.base_url = base_url;
        }
        if (extract_string(content, R"(\"openai\"[\s\S]*?\"model\")", model)) {
            config.translator_options.model = model;
        }
        if (extract_int(content, R"(\"openai\"[\s\S]*?\"max_tokens\")", max_tokens)) {
            config.translator_options.max_tokens = max_tokens;
        }
        if (extract_double(content, R"(\"openai\"[\s\S]*?\"temperature\")", temperature)) {
            config.translator_options.temperature = temperature;
        }
        if (extract_int(content, R"(\"openai\"[\s\S]*?\"timeout\")", timeout)) {
            config.translator_options.timeout_seconds = timeout;
        }
        if (extract_int(content, R"(\"openai\"[\s\S]*?\"retry_count\")", retry)) {
            config.translator_options.retry_count = retry;
        }
    }

    return true;
}

bool ConfigManager::apply_model_dir_from_config(const std::filesystem::path& user_config_path,
                                                const std::filesystem::path& default_config_path) {
    // 优先读取用户配置
    std::string content = read_file(user_config_path);
    if (content.empty()) {
        content = read_file(default_config_path);
    }
    if (content.empty()) {
        return false;
    }

    std::string whisper_model_dir;
    if (extract_string(content, R"(\"model_dir\")", whisper_model_dir)) {
        if (!whisper_model_dir.empty()) {
            v2s::ModelManager::set_model_dir(std::filesystem::path(whisper_model_dir));
            return true;
        }
    }
    return false;
}

bool ConfigManager::save_model_dir_to_config(const std::filesystem::path& user_config_path,
                                             const std::filesystem::path& default_config_path,
                                             const std::filesystem::path& dir) {
    try {
        // 读取用户配置，若不存在则以默认配置为模板
        std::string content = read_file(user_config_path);
        if (content.empty()) {
            content = read_file(default_config_path);
        }

        // 如果仍为空，则创建最小可用配置结构
        if (content.empty()) {
            content = std::string("{\n  \"whisper\": {\n    \"model_dir\": \"") + dir.generic_string() + "\"\n  }\n}\n";
        } else {
            // 先尝试替换已存在的 model_dir 字段
            std::regex model_dir_re(R"(\"model_dir\"\s*:\s*\"[^\"]*\")", std::regex::icase);
            if (std::regex_search(content, model_dir_re)) {
                content = std::regex_replace(content, model_dir_re,
                                             std::string("\"model_dir\": \"") + dir.generic_string() + "\"");
            } else {
                // 尝试插入到 whisper 段中（优先在 model_path 后插入）
                std::size_t mp = content.find("\"model_path\"");
                if (mp != std::string::npos) {
                    // 找到下一行结束位置
                    std::size_t insert_pos = content.find('\n', mp);
                    if (insert_pos == std::string::npos) insert_pos = mp + 1;
                    std::string insertion = std::string("\n        \"model_dir\": \"") + dir.generic_string() + "\",";
                    content.insert(insert_pos, insertion);
                } else {
                    // 在 whisper 对象开头插入
                    std::size_t wpos = content.find("\"whisper\"");
                    if (wpos != std::string::npos) {
                        std::size_t brace_pos = content.find('{', wpos);
                        if (brace_pos != std::string::npos) {
                            std::size_t insert_pos = brace_pos + 1;
                            std::string insertion = std::string("\n        \"model_dir\": \"") + dir.generic_string() + "\",";
                            content.insert(insert_pos, insertion);
                        } else {
                            // 未找到合适位置，直接在文件末尾追加一个 whisper 块
                            content += std::string("\n, \"whisper\": { \"model_dir\": \"") + dir.generic_string() + "\" }\n";
                        }
                    } else {
                        // 无 whisper 段，追加一个
                        if (!content.empty() && content.back() == '}') {
                            // 尝试在末尾前插入（简单处理，可能不严格JSON）
                            content.insert(content.size() - 1, std::string(
                                "\n,  \"whisper\": { \"model_dir\": \"") + dir.generic_string() + "\" }\n");
                        } else {
                            content += std::string("\n\"whisper\": { \"model_dir\": \"") + dir.generic_string() + "\" }\n";
                        }
                    }
                }
            }
        }

        // 写回到用户配置文件
        std::filesystem::create_directories(user_config_path.parent_path());
        std::ofstream ofs(user_config_path, std::ios::out | std::ios::trunc);
        if (!ofs.is_open()) return false;
        ofs << content;
        ofs.close();
        return true;
    } catch (...) {
        return false;
    }
}

} // namespace v2s