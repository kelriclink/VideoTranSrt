#include "video2srt_native/config_manager.hpp"
#include "video2srt_native/model_manager.hpp"
#include <fstream>
#include <sstream>
#include <nlohmann/json.hpp>
// 获取可执行文件路径所需的系统头文件
#if defined(_WIN32)
#  include <windows.h>
#elif defined(__APPLE__)
#  include <mach-o/dyld.h>
#else
#  include <unistd.h>
#endif

namespace v2s {
using nlohmann::json;

std::filesystem::path ConfigManager::get_executable_dir() {
#if defined(_WIN32)
    wchar_t buffer[MAX_PATH];
    DWORD len = GetModuleFileNameW(nullptr, buffer, MAX_PATH);
    if (len == 0 || len >= MAX_PATH) {
        // 退回到当前工作目录（极少数情况下）
        return std::filesystem::current_path();
    }
    std::filesystem::path exe_path(buffer);
    return exe_path.parent_path();
#elif defined(__APPLE__)
    char buffer[1024];
    uint32_t size = sizeof(buffer);
    if (_NSGetExecutablePath(buffer, &size) != 0) {
        std::string dyn; dyn.resize(size);
        _NSGetExecutablePath(dyn.data(), &size);
        return std::filesystem::path(dyn).parent_path();
    }
    return std::filesystem::path(buffer).parent_path();
#else
    char buffer[4096];
    ssize_t len = ::readlink("/proc/self/exe", buffer, sizeof(buffer) - 1);
    if (len <= 0) {
        return std::filesystem::current_path();
    }
    buffer[len] = '\0';
    return std::filesystem::path(buffer).parent_path();
#endif
}

std::filesystem::path ConfigManager::resolve_to_app_dir(const std::filesystem::path& p) {
    if (p.is_absolute()) return p;
    return get_executable_dir() / p;
}

std::string ConfigManager::read_file(const std::filesystem::path& path) {
    std::ifstream f(path, std::ios::in);
    if (!f.is_open()) return {};
    std::ostringstream ss;
    ss << f.rdbuf();
    return ss.str();
}

// 使用 nlohmann_json 读取并解析 JSON 文件
static bool read_json_file(const std::filesystem::path& path, json& out) {
    std::ifstream f(path);
    if (!f.is_open()) return false;
    try {
        out = json::parse(f, /*callback*/nullptr, /*allow_exceptions*/true, /*ignore_comments*/true);
        return true;
    } catch (...) {
        return false;
    }
}

bool ConfigManager::apply_default_config(ProcessingConfig& config,
                                         const std::filesystem::path& config_path) {
    const auto abs_config = resolve_to_app_dir(config_path);
    json j;
    if (!read_json_file(abs_config, j)) {
        return false;
    }

    // general.default_translator
    if (j.contains("general") && j["general"].is_object()) {
        const auto& g = j["general"];
        if (g.contains("default_translator") && g["default_translator"].is_string()) {
            std::string default_translator = g["default_translator"].get<std::string>();
            if (config.translator_type == "simple" || config.translator_type.empty()) {
                config.translator_type = default_translator;
            }
        }
    }

    // whisper.*
    if (j.contains("whisper") && j["whisper"].is_object()) {
        const auto& w = j["whisper"];
        if (w.contains("model_size") && w["model_size"].is_string()) {
            std::string model_size = w["model_size"].get<std::string>();
            if (config.model_size == "base") {
                config.model_size = model_size;
            }
        }
        if (w.contains("language") && w["language"].is_string()) {
            std::string language = w["language"].get<std::string>();
            if (!config.language.has_value() || config.language->empty()) {
                if (language != "auto") {
                    config.language = language;
                }
            }
        }
        if (w.contains("model_dir") && w["model_dir"].is_string()) {
            std::string model_dir = w["model_dir"].get<std::string>();
            if (!model_dir.empty()) {
                std::filesystem::path dir(model_dir);
                if (!dir.is_absolute()) {
                    dir = get_executable_dir() / dir;
                }
                v2s::ModelManager::set_model_dir(dir);
            }
        }
        if (w.contains("device") && w["device"].is_string()) {
            std::string device = w["device"].get<std::string>();
            if (device == "cuda" || device == "gpu") {
                config.use_gpu = true;
                config.device = "cuda";
            } else if (device == "cpu") {
                config.use_gpu = false;
                config.device = "cpu";
            }
        }
    }

    // translators.google
    if (j.contains("translators") && j["translators"].is_object()) {
        const auto& t = j["translators"];
        if (t.contains("google") && t["google"].is_object()) {
            const auto& ggl = t["google"];
            bool google_enabled = ggl.value("enabled", false);
            if (config.translator_type == "google" && google_enabled) {
                config.translator_options.timeout_seconds = ggl.value("timeout", config.translator_options.timeout_seconds);
                config.translator_options.retry_count = ggl.value("retry_count", config.translator_options.retry_count);
                config.translator_options.ssl_bypass = ggl.value("use_ssl_bypass", config.translator_options.ssl_bypass);
                // 默认 base_url（注：非官方端点）
                config.translator_options.base_url = "https://translate.googleapis.com";
            }
        }
        if (t.contains("openai") && t["openai"].is_object()) {
            const auto& oa = t["openai"];
            bool openai_enabled = oa.value("enabled", false);
            if (config.translator_type == "openai" && openai_enabled) {
                if (oa.contains("api_key") && oa["api_key"].is_string()) {
                    config.translator_options.api_key = oa["api_key"].get<std::string>();
                }
                if (oa.contains("base_url") && oa["base_url"].is_string()) {
                    config.translator_options.base_url = oa["base_url"].get<std::string>();
                }
                if (oa.contains("model") && oa["model"].is_string()) {
                    config.translator_options.model = oa["model"].get<std::string>();
                }
                config.translator_options.max_tokens = oa.value("max_tokens", config.translator_options.max_tokens);
                config.translator_options.temperature = oa.value("temperature", config.translator_options.temperature);
                config.translator_options.timeout_seconds = oa.value("timeout", config.translator_options.timeout_seconds);
                config.translator_options.retry_count = oa.value("retry_count", config.translator_options.retry_count);
            }
        }
    }

    return true;
}

bool ConfigManager::apply_model_dir_from_config(const std::filesystem::path& user_config_path,
                                                const std::filesystem::path& default_config_path) {
    const auto abs_user = resolve_to_app_dir(user_config_path);
    const auto abs_default = resolve_to_app_dir(default_config_path);
    json j;
    bool loaded = false;
    if (read_json_file(abs_user, j)) {
        loaded = true;
    } else if (read_json_file(abs_default, j)) {
        loaded = true;
    }
    if (!loaded) return false;

    if (j.contains("whisper") && j["whisper"].is_object()) {
        const auto& w = j["whisper"];
        if (w.contains("model_dir") && w["model_dir"].is_string()) {
            std::string model_dir = w["model_dir"].get<std::string>();
            if (!model_dir.empty()) {
                std::filesystem::path dir(model_dir);
                if (!dir.is_absolute()) {
                    dir = get_executable_dir() / dir;
                }
                v2s::ModelManager::set_model_dir(dir);
                return true;
            }
        }
    }
    return false;
}

bool ConfigManager::save_model_dir_to_config(const std::filesystem::path& user_config_path,
                                             const std::filesystem::path& default_config_path,
                                             const std::filesystem::path& dir) {
    try {
        const auto abs_user = resolve_to_app_dir(user_config_path);
        const auto abs_default = resolve_to_app_dir(default_config_path);

        json j;
        if (!read_json_file(abs_user, j)) {
            if (!read_json_file(abs_default, j)) {
                // 构造最小配置
                j = json::object();
            }
        }

        // 确保 whisper 对象存在
        if (!j.contains("whisper") || !j["whisper"].is_object()) {
            j["whisper"] = json::object();
        }
        j["whisper"]["model_dir"] = dir.string();

        // 写回到用户配置文件（美化缩进）
        std::filesystem::create_directories(abs_user.parent_path());
        std::ofstream ofs(abs_user, std::ios::out | std::ios::trunc);
        if (!ofs.is_open()) return false;
        ofs << j.dump(2);
        ofs.close();
        return true;
    } catch (...) {
        return false;
    }
}

// 以上基于正则/字符串的伪 JSON 操作全部移除，统一改用 nlohmann_json 进行可靠解析与写入

bool ConfigManager::save_user_config(const std::filesystem::path& user_config_path,
                                     const std::filesystem::path& default_config_path,
                                     const ProcessingConfig& cfg) {
    try {
        const auto abs_user = resolve_to_app_dir(user_config_path);
        const auto abs_default = resolve_to_app_dir(default_config_path);

        json j;
        if (!read_json_file(abs_user, j)) {
            if (!read_json_file(abs_default, j)) {
                // 构建一个带基本结构的骨架
                j = json{
                    {"general", json{{"default_translator", "simple"}}},
                    {"whisper", json{{"model_size", "base"}, {"language", "auto"}, {"device", "auto"}}},
                    {"translators", json{
                        {"google", json{{"enabled", false}, {"timeout", 15}, {"retry_count", 3}, {"use_ssl_bypass", false}}},
                        {"openai", json{{"enabled", false}, {"api_key", ""}, {"base_url", "https://api.openai.com/v1"}, {"model", "gpt-3.5-turbo"}, {"max_tokens", 4000}, {"temperature", 0.3}, {"timeout", 15}, {"retry_count", 3}}}
                    }}
                };
            }
        }

        // 确保必要的对象存在
        if (!j.contains("general") || !j["general"].is_object()) j["general"] = json::object();
        if (!j.contains("whisper") || !j["whisper"].is_object()) j["whisper"] = json::object();
        if (!j.contains("translators") || !j["translators"].is_object()) j["translators"] = json::object();
        if (!j["translators"].contains("google") || !j["translators"]["google"].is_object()) j["translators"]["google"] = json::object();
        if (!j["translators"].contains("openai") || !j["translators"]["openai"].is_object()) j["translators"]["openai"] = json::object();

        // general.default_translator
        std::string default_translator = cfg.translator_type.empty() ? std::string("simple") : cfg.translator_type;
        j["general"]["default_translator"] = default_translator;

        // whisper.*
        std::string lang = cfg.language.has_value() ? cfg.language.value() : std::string("auto");
        std::string device = (!cfg.device.empty()) ? cfg.device : (cfg.use_gpu ? std::string("gpu") : std::string("cpu"));
        j["whisper"]["model_size"] = cfg.model_size;
        j["whisper"]["language"] = lang;
        j["whisper"]["device"] = device;

        // translators.google
        bool google_enabled = (cfg.translator_type == "google");
        j["translators"]["google"]["enabled"] = google_enabled;
        j["translators"]["google"]["timeout"] = cfg.translator_options.timeout_seconds;
        j["translators"]["google"]["retry_count"] = cfg.translator_options.retry_count;
        j["translators"]["google"]["use_ssl_bypass"] = cfg.translator_options.ssl_bypass;

        // translators.openai
        bool openai_enabled = (cfg.translator_type == "openai");
        j["translators"]["openai"]["enabled"] = openai_enabled;
        j["translators"]["openai"]["api_key"] = cfg.translator_options.api_key;
        j["translators"]["openai"]["base_url"] = cfg.translator_options.base_url.empty() ? std::string("https://api.openai.com/v1") : cfg.translator_options.base_url;
        j["translators"]["openai"]["model"] = cfg.translator_options.model.empty() ? std::string("gpt-3.5-turbo") : cfg.translator_options.model;
        j["translators"]["openai"]["max_tokens"] = (cfg.translator_options.max_tokens > 0 ? cfg.translator_options.max_tokens : 4000);
        j["translators"]["openai"]["temperature"] = cfg.translator_options.temperature;
        j["translators"]["openai"]["timeout"] = cfg.translator_options.timeout_seconds;
        j["translators"]["openai"]["retry_count"] = cfg.translator_options.retry_count;

        // 写回（美化缩进）
        std::filesystem::create_directories(abs_user.parent_path());
        std::ofstream ofs(abs_user, std::ios::out | std::ios::trunc);
        if (!ofs.is_open()) return false;
        ofs << j.dump(2);
        ofs.close();
        return true;
    } catch (...) {
        return false;
    }
}

} // namespace v2s