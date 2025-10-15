#pragma once

#include "models.hpp"
#include <string>
#include <vector>
#include <filesystem>
#include <functional>

namespace v2s {

/**
 * 模型管理器：负责 Whisper.cpp 模型的目录、状态与下载
 * 参考 Python 版的模型管理思想，提供最常用的管理能力
 */
class ModelManager {
public:
    using DownloadProgress = std::function<void(const std::string& model_name, size_t downloaded_bytes, size_t total_bytes)>;

    /**
     * 设置/获取模型目录（默认：当前目录下 models/）
     */
    static void set_model_dir(const std::filesystem::path& dir);
    static std::filesystem::path get_model_dir();

    /**
     * 列出支持的模型（tiny/base/small/medium/large）及其状态
     */
    static std::vector<ModelInfo> list_models();

    /**
     * 获取指定大小模型的本地文件路径
     */
    static std::filesystem::path get_model_file_path(const std::string& size);

    /**
     * 是否已下载指定模型
     */
    static bool is_downloaded(const std::string& size);

    /**
     * 下载指定模型（从 HuggingFace 仓库），如果目录不存在则创建
     * 返回是否下载成功
     */
    static bool download_model(const std::string& size, DownloadProgress progress_cb = nullptr);

    /**
     * 删除指定模型文件
     */
    static bool delete_model(const std::string& size);

    /**
     * 构造模型文件名（ggml-<size>.bin）
     */
    static std::string build_model_filename(const std::string& size);

    /**
     * 获取模型下载 URL（默认 HuggingFace ggerganov/whisper.cpp 仓库）
     */
    static std::string build_model_url(const std::string& size);

private:
    static std::filesystem::path s_model_dir;
    static std::string normalize_size(const std::string& size);
};

} // namespace v2s