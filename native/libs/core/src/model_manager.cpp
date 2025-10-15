#include "video2srt_native/model_manager.hpp"
#include <algorithm>
#include <fstream>
#include <iostream>
#include <sstream>

#if defined(_WIN32)
#include <windows.h>
#include <winhttp.h>
#pragma comment(lib, "winhttp.lib")
#endif

namespace v2s {

std::filesystem::path ModelManager::s_model_dir = std::filesystem::current_path() / "models";

void ModelManager::set_model_dir(const std::filesystem::path& dir) {
    s_model_dir = dir;
}

std::filesystem::path ModelManager::get_model_dir() {
    return s_model_dir;
}

std::string ModelManager::normalize_size(const std::string& size) {
    std::string s = size;
    std::transform(s.begin(), s.end(), s.begin(), ::tolower);
    // 支持更多 whisper.cpp 模型名（含 .en、large 版本与 turbo 变体）
    if (s == "tiny" || s == "base" || s == "small" || s == "medium") return s;
    if (s == "large") return "large-v3"; // 默认 large 映射到 large-v3
    // 允许直接传入更具体的模型名
    if (s == "tiny.en" || s == "base.en" || s == "small.en" || s == "medium.en"
        || s == "large-v1" || s == "large-v2" || s == "large-v3" || s == "large-v3-turbo") return s;
    return "base";
}

std::string ModelManager::build_model_filename(const std::string& size) {
    // large 默认使用 v3 文件名，其他保持与 whisper.cpp 仓库一致
    std::string norm = normalize_size(size);
    return std::string("ggml-") + norm + ".bin";
}

std::filesystem::path ModelManager::get_model_file_path(const std::string& size) {
    return get_model_dir() / build_model_filename(size);
}

std::string ModelManager::build_model_url(const std::string& size) {
    // 参考 whisper.cpp 官方模型仓库（如有需要可改为配置文件）
    // 形如：https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-base.bin
    return std::string("https://huggingface.co/ggerganov/whisper.cpp/resolve/main/") + build_model_filename(size);
}

bool ModelManager::is_downloaded(const std::string& size) {
    auto path = get_model_file_path(size);
    return std::filesystem::exists(path) && std::filesystem::file_size(path) > 0;
}

std::vector<ModelInfo> ModelManager::list_models() {
    std::vector<ModelInfo> infos;
    // 展示更全面的 whisper.cpp 模型列表（含英文版、大模型版本、量化与 diarize 变体）
    const char* models[] = {
        "tiny", "tiny.en",
        "base", "base.en",
        "small", "small.en", "small.en-tdrz",
        "medium", "medium.en",
        "large-v1", "large-v2", "large-v3", "large-v3-turbo",
        "large-v2-q5_0", "large-v3-q5_0", "large-v3-turbo-q5_0"
    };
    for (const char* s : models) {
        ModelInfo info;
        info.name = std::string("whisper.cpp ") + s;
        info.size = s; // 此处 size 即模型标识
        info.type = "whisper.cpp";
        auto path = get_model_file_path(s);
        if (std::filesystem::exists(path)) {
            info.is_downloaded = true;
            try {
                info.file_size = std::filesystem::file_size(path);
            } catch (...) {}
        } else {
            info.is_downloaded = false;
        }
        info.download_url = build_model_url(s);
        infos.push_back(std::move(info));
    }
    return infos;
}

bool ModelManager::download_model(const std::string& size, DownloadProgress progress_cb) {
    std::filesystem::create_directories(get_model_dir());
    auto path = get_model_file_path(size);
    auto primary_url = build_model_url(size);

    // 加入多个下载镜像以提高在受限网络环境中的可达性
    // 参考：
    // - 官方 Hugging Face 仓库：https://huggingface.co/ggerganov/whisper.cpp/tree/main
    // - HF 国内镜像（社区维护）：https://hf-mirror.com/ggerganov/whisper.cpp/tree/main
    std::vector<std::string> candidate_urls = {
        primary_url,
        std::string("https://hf-mirror.com/ggerganov/whisper.cpp/resolve/main/") + build_model_filename(size)
    };

#if defined(_WIN32)
    auto parse_https_url = [](const std::wstring& wurl, std::wstring& hostOut, std::wstring& pathOut) -> bool {
        const std::wstring prefix = L"https://";
        if (wurl.compare(0, prefix.size(), prefix) != 0) return false;
        size_t pos = wurl.find(L'/', prefix.size());
        if (pos == std::wstring::npos) {
            hostOut = wurl.substr(prefix.size());
            pathOut = L"/";
        } else {
            hostOut = wurl.substr(prefix.size(), pos - prefix.size());
            pathOut = wurl.substr(pos);
        }
        return !hostOut.empty();
    };

    HINTERNET hSession = WinHttpOpen(L"Video2SRT-Native/ModelManager",
                                     WINHTTP_ACCESS_TYPE_DEFAULT_PROXY,
                                     WINHTTP_NO_PROXY_NAME,
                                     WINHTTP_NO_PROXY_BYPASS, 0);
    if (!hSession) return false;

    // 设置超时
    WinHttpSetTimeouts(hSession, 30000, 30000, 30000, 30000); // 30s 连接/发送/接收/解析

    const int kMaxRedirect = 5;
    bool success = false;
    size_t totalBytes = 0;

    for (size_t i = 0; i < candidate_urls.size() && !success; ++i) {
        const std::string& url = candidate_urls[i];
        std::wstring initialUrl(url.begin(), url.end());
        std::wstring host, wpath;
        if (!parse_https_url(initialUrl, host, wpath)) {
            std::cerr << "模型下载 URL 解析失败: " << url << std::endl;
            continue;
        }

        std::cerr << "[ModelManager] 尝试下载地址 (" << (i+1) << "/" << candidate_urls.size() << "): " << url << std::endl;

        // 每个地址单独写入，失败则清理零字节文件
        std::ofstream ofs(path, std::ios::binary | std::ios::trunc);
        if (!ofs.is_open()) {
            std::cerr << "[ModelManager] 打开输出文件失败: " << path.string() << std::endl;
            continue;
        }

        int redirectCount = 0;
        size_t downloaded = 0;

        while (redirectCount <= kMaxRedirect) {
            std::cerr << "[ModelManager] 请求: https://" << std::string(host.begin(), host.end())
                      << std::string(wpath.begin(), wpath.end()) << std::endl;

            HINTERNET hConnect = WinHttpConnect(hSession, host.c_str(), INTERNET_DEFAULT_HTTPS_PORT, 0);
            if (!hConnect) {
                std::cerr << "[ModelManager] WinHttpConnect 失败, 错误码: " << GetLastError() << std::endl;
                break;
            }

            HINTERNET hRequest = WinHttpOpenRequest(hConnect, L"GET", wpath.c_str(),
                                                    NULL, WINHTTP_NO_REFERER,
                                                    WINHTTP_DEFAULT_ACCEPT_TYPES,
                                                    WINHTTP_FLAG_SECURE);
            if (!hRequest) { 
                std::cerr << "[ModelManager] WinHttpOpenRequest 失败, 错误码: " << GetLastError() << std::endl;
                WinHttpCloseHandle(hConnect);
                break; 
            }

            // 限制协议为 TLS1.2，避免旧系统默认不启用导致握手失败
            DWORD secureProtocols = WINHTTP_FLAG_SECURE_PROTOCOL_TLS1_2;
            WinHttpSetOption(hRequest, WINHTTP_OPTION_SECURE_PROTOCOLS, &secureProtocols, sizeof(secureProtocols));

            if (!WinHttpSendRequest(hRequest, WINHTTP_NO_ADDITIONAL_HEADERS, 0,
                                    WINHTTP_NO_REQUEST_DATA, 0, 0, 0)) {
                std::cerr << "[ModelManager] WinHttpSendRequest 失败, 错误码: " << GetLastError() << std::endl;
                WinHttpCloseHandle(hRequest); WinHttpCloseHandle(hConnect);
                break; // 尝试下一个地址
            }
            if (!WinHttpReceiveResponse(hRequest, NULL)) {
                std::cerr << "[ModelManager] WinHttpReceiveResponse 失败, 错误码: " << GetLastError() << std::endl;
                WinHttpCloseHandle(hRequest); WinHttpCloseHandle(hConnect);
                break; // 尝试下一个地址
            }

            // 检查状态码
            DWORD statusCode = 0; DWORD scSize = sizeof(statusCode);
            if (!WinHttpQueryHeaders(hRequest, WINHTTP_QUERY_STATUS_CODE | WINHTTP_QUERY_FLAG_NUMBER,
                                     WINHTTP_HEADER_NAME_BY_INDEX, &statusCode, &scSize, WINHTTP_NO_HEADER_INDEX)) {
                std::cerr << "[ModelManager] 查询状态码失败, 错误码: " << GetLastError() << std::endl;
                statusCode = 0;
            }

            std::cerr << "[ModelManager] 响应状态码: " << statusCode << std::endl;
            if (statusCode >= 300 && statusCode < 400) {
                // 重定向：读取 Location，解析新 host/path
                DWORD locSize = 0;
                WinHttpQueryHeaders(hRequest, WINHTTP_QUERY_LOCATION, WINHTTP_HEADER_NAME_BY_INDEX,
                                    NULL, &locSize, WINHTTP_NO_HEADER_INDEX);
                if (GetLastError() == ERROR_INSUFFICIENT_BUFFER && locSize > 0) {
                    std::wstring location; location.resize(locSize / sizeof(wchar_t));
                    if (WinHttpQueryHeaders(hRequest, WINHTTP_QUERY_LOCATION, WINHTTP_HEADER_NAME_BY_INDEX,
                                            location.data(), &locSize, WINHTTP_NO_HEADER_INDEX)) {
                        // 去掉可能的尾部空字符
                        if (!location.empty() && location.back() == L'\0') location.pop_back();
                        std::wstring newHost, newPath;
                        if (parse_https_url(location, newHost, newPath)) {
                            std::cerr << "[ModelManager] 重定向至: https://" << std::string(newHost.begin(), newHost.end())
                                      << std::string(newPath.begin(), newPath.end()) << std::endl;
                            host = std::move(newHost);
                            wpath = std::move(newPath);
                            redirectCount++;
                            WinHttpCloseHandle(hRequest);
                            WinHttpCloseHandle(hConnect);
                            continue; // 重新发起请求
                        }
                        std::cerr << "[ModelManager] Location 非 https URL 或解析失败" << std::endl;
                    }
                }
                // 未能处理重定向，视为失败，尝试下一个地址
                WinHttpCloseHandle(hRequest);
                WinHttpCloseHandle(hConnect);
                break;
            }

            // 读取 Content-Length（可能为 0 或缺失）
            DWORD dwSize = sizeof(DWORD);
            DWORD dwIndex = 0;
            DWORD content_length = 0;
            WinHttpQueryHeaders(hRequest, WINHTTP_QUERY_CONTENT_LENGTH | WINHTTP_QUERY_FLAG_NUMBER,
                                WINHTTP_HEADER_NAME_BY_INDEX, &content_length, &dwSize, &dwIndex);
            totalBytes = static_cast<size_t>(content_length);

            // 当无法获取总大小时，使用不确定进度
            std::string buffer;
            buffer.resize(1 << 16); // 64KB

            bool readOk = false;
            for (;;) {
                DWORD avail = 0;
                if (!WinHttpQueryDataAvailable(hRequest, &avail)) { readOk = false; break; }
                if (avail == 0) { readOk = true; break; }
                DWORD read = 0;
                if (!WinHttpReadData(hRequest, buffer.data(), std::min<DWORD>(avail, (DWORD)buffer.size()), &read)) { readOk = false; break; }
                if (read == 0) { readOk = true; break; }
                ofs.write(buffer.data(), read);
                downloaded += read;
                if (progress_cb) {
                    progress_cb(normalize_size(size), downloaded, totalBytes);
                }
            }

            WinHttpCloseHandle(hRequest);
            WinHttpCloseHandle(hConnect);

            success = readOk && (std::filesystem::exists(path) && std::filesystem::file_size(path) > 0);
            break; // 已完成读取或失败，退出重定向循环
        }

        ofs.close();

        if (!success) {
            // 失败时删除空文件
            try { if (std::filesystem::exists(path) && std::filesystem::file_size(path) == 0) std::filesystem::remove(path); } catch (...) {}
        }
    }

    WinHttpCloseHandle(hSession);

    return success;
#else
    (void)progress_cb;
    std::cerr << "当前平台未实现模型下载（仅Windows WinHTTP提供内置实现）\n";
    return false;
#endif
}

bool ModelManager::delete_model(const std::string& size) {
    auto path = get_model_file_path(size);
    try {
        if (std::filesystem::exists(path)) {
            std::filesystem::remove(path);
            return true;
        }
        return false;
    } catch (...) {
        return false;
    }
}

} // namespace v2s