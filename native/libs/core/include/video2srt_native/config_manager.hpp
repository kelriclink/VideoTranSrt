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

    /**
     * 将当前设置保存到用户配置（config/config.json），用于 GUI 持久化。
     * 仅保存在默认配置中已存在或核心能识别的字段：
     * - general.default_translator
     * - whisper.model_size / whisper.language / whisper.device
     * - translators.google: enabled/timeout/retry_count/use_ssl_bypass
     * - translators.openai: enabled/api_key/base_url/model/max_tokens/temperature/timeout/retry_count
     * @param user_config_path 用户配置文件路径（默认：config/config.json）
     * @param default_config_path 默认配置文件路径（默认：config/default_config.json）
     * @param config 当前处理配置（从 GUI 采集）
     * @return 是否保存成功
     */
    static bool save_user_config(const std::filesystem::path& user_config_path,
                                 const std::filesystem::path& default_config_path,
                                 const ProcessingConfig& config);

private:
    // 返回可执行文件所在目录（跨平台）。
    static std::filesystem::path get_executable_dir();
    // 若传入为相对路径，则按“可执行文件目录”为基准进行解析；绝对路径保持不变。
    static std::filesystem::path resolve_to_app_dir(const std::filesystem::path& p);
    static std::string read_file(const std::filesystem::path& path);
};

} // namespace v2s