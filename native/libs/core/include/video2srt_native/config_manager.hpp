#pragma once

#include "models.hpp"
#include <filesystem>

namespace v2s {

/**
 * 配置管理器：从 config/default_config.json 读取默认参数并合并到 ProcessingConfig
 */
class ConfigManager {
public:
    /**
     * 读取并应用默认配置到传入的 ProcessingConfig。
     * CLI 未设置的字段将被默认配置填充。
     * @param config 处理配置（输入为CLI基础配置，输出为合并后的配置）
     * @param config_path 配置文件路径（默认：config/default_config.json）
     * @return 是否成功读取并应用
     */
    static bool apply_default_config(ProcessingConfig& config,
                                     const std::filesystem::path& config_path = std::filesystem::path("config/default_config.json"));

    /**
     * 从配置文件读取并应用模型目录（model_dir）到 ModelManager。
     * 先尝试用户配置（config/config.json），若未找到或为空则回退到默认配置（config/default_config.json）。
     * @param user_config_path 用户配置文件路径（默认：config/config.json）
     * @param default_config_path 默认配置文件路径（默认：config/default_config.json）
     * @return 是否成功从配置中读取并应用了 model_dir
     */
    static bool apply_model_dir_from_config(const std::filesystem::path& user_config_path = std::filesystem::path("config/config.json"),
                                            const std::filesystem::path& default_config_path = std::filesystem::path("config/default_config.json"));

    /**
     * 将模型目录（model_dir）保存/更新到用户配置文件（config/config.json）。
     * 如果用户配置不存在，将以默认配置为模板创建后再写入。
     * @param user_config_path 用户配置文件路径（默认：config/config.json）
     * @param default_config_path 默认配置文件路径（默认：config/default_config.json）
     * @param dir 模型目录路径
     * @return 是否保存成功
     */
    static bool save_model_dir_to_config(const std::filesystem::path& user_config_path,
                                         const std::filesystem::path& default_config_path,
                                         const std::filesystem::path& dir);

private:
    static std::string read_file(const std::filesystem::path& path);
    static bool extract_bool(const std::string& content, const std::string& key, bool& out);
    static bool extract_int(const std::string& content, const std::string& key, int& out);
    static bool extract_double(const std::string& content, const std::string& key, double& out);
    static bool extract_string(const std::string& content, const std::string& key, std::string& out);
};

} // namespace v2s