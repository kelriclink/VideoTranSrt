#include "video2srt_native/openai_translator.hpp"

#ifdef _WIN32
#include <windows.h>
#include <winhttp.h>
#pragma comment(lib, "winhttp.lib")
#endif

#include <sstream>
#include <iomanip>
#include <regex>

namespace v2s {

OpenAITranslator::OpenAITranslator(const TranslatorOptions& opts)
    : opts_(opts) {}

static bool parse_url(const std::string& base_url, std::wstring& host, INTERNET_PORT& port, bool& use_https, std::wstring& base_path) {
    // Very simple URL parser, expects http(s)://host[:port][/path]
    std::string url = base_url;
    use_https = false;
    port = 0;

    if (url.rfind("https://", 0) == 0) {
        use_https = true;
        url = url.substr(8);
    } else if (url.rfind("http://", 0) == 0) {
        use_https = false;
        url = url.substr(7);
    }

    std::string host_port;
    std::string path;
    auto slash_pos = url.find('/');
    if (slash_pos == std::string::npos) {
        host_port = url;
        path = "/";
    } else {
        host_port = url.substr(0, slash_pos);
        path = url.substr(slash_pos);
        if (path.empty()) path = "/";
    }

    auto colon_pos = host_port.find(':');
    if (colon_pos != std::string::npos) {
        host = std::wstring(host_port.begin(), host_port.begin() + colon_pos);
        try {
            port = static_cast<INTERNET_PORT>(std::stoi(host_port.substr(colon_pos + 1)));
        } catch (...) {
            port = use_https ? INTERNET_DEFAULT_HTTPS_PORT : INTERNET_DEFAULT_HTTP_PORT;
        }
    } else {
        host = std::wstring(host_port.begin(), host_port.end());
        port = use_https ? INTERNET_DEFAULT_HTTPS_PORT : INTERNET_DEFAULT_HTTP_PORT;
    }

    base_path = std::wstring(path.begin(), path.end());
    return !host.empty();
}

static std::string json_escape(const std::string& s) {
    std::ostringstream oss;
    for (char c : s) {
        switch (c) {
            case '"': oss << "\\\""; break;
            case '\\': oss << "\\\\"; break;
            case '\n': oss << "\\n"; break;
            case '\r': oss << "\\r"; break;
            case '\t': oss << "\\t"; break;
            default:
                if (static_cast<unsigned char>(c) < 0x20) {
                    oss << "\\u" << std::hex << std::setw(4) << std::setfill('0') << (int)(unsigned char)c;
                } else {
                    oss << c;
                }
        }
    }
    return oss.str();
}

std::string OpenAITranslator::translate_text(const std::string& text,
                                             const std::string& target_language,
                                             const std::string& source_language) {
#ifndef _WIN32
    // 非 Windows 暂不支持，直接返回原文
    return text;
#else
    if (opts_.api_key.empty()) {
        return text; // 无 API key 时返回原文
    }

    const std::string base_url = opts_.base_url.empty() ? std::string("https://api.openai.com/v1") : opts_.base_url;
    std::wstring host, base_path;
    INTERNET_PORT port;
    bool use_https;
    if (!parse_url(base_url, host, port, use_https, base_path)) {
        return text;
    }

    // 构造请求路径
    std::wstring path = base_path;
    if (path.back() == L'/') {
        path += L"chat/completions";
    } else {
        path += L"/chat/completions";
    }

    // 构造请求体（Chat Completions）
    double temperature = opts_.temperature;
    if (temperature < 0.0) temperature = 0.0;
    if (temperature > 2.0) temperature = 2.0;
    int max_tokens = opts_.max_tokens > 0 ? opts_.max_tokens : 1024;
    const std::string model = opts_.model.empty() ? std::string("gpt-4o-mini") : opts_.model;

    std::ostringstream body;
    body << "{\n"
         << "  \"model\": \"" << json_escape(model) << "\",\n"
         << "  \"messages\": [\n"
         << "    {\"role\": \"system\", \"content\": \"You are a professional translator. Translate text from "
         << json_escape(source_language.empty() ? std::string("auto") : source_language)
         << " to " << json_escape(target_language) << ". Output ONLY the translated text without any explanations.\"},\n"
         << "    {\"role\": \"user\", \"content\": \"" << json_escape(text) << "\"}\n"
         << "  ],\n"
         << "  \"temperature\": " << std::fixed << std::setprecision(2) << temperature << ",\n"
         << "  \"max_tokens\": " << max_tokens << "\n"
         << "}";
    std::string body_str = body.str();

    HINTERNET hSession = nullptr, hConnect = nullptr, hRequest = nullptr;
    std::string result_text = text;
    DWORD dwFlags = 0;
    if (use_https) {
        dwFlags |= WINHTTP_FLAG_SECURE;
    }
    if (opts_.ssl_bypass) {
        // Relax SSL verification (not recommended)
        dwFlags |= WINHTTP_FLAG_SECURE;
    }

    hSession = WinHttpOpen(L"v2s-openai-translator/1.0",
                           WINHTTP_ACCESS_TYPE_DEFAULT_PROXY,
                           WINHTTP_NO_PROXY_NAME,
                           WINHTTP_NO_PROXY_BYPASS, 0);
    if (!hSession) {
        return text;
    }

    if (opts_.timeout_seconds > 0) {
        int t = opts_.timeout_seconds * 1000;
        WinHttpSetTimeouts(hSession, t, t, t, t);
    }

    hConnect = WinHttpConnect(hSession, host.c_str(), port, 0);
    if (!hConnect) {
        WinHttpCloseHandle(hSession);
        return text;
    }

    hRequest = WinHttpOpenRequest(hConnect, L"POST", path.c_str(), NULL,
                                  WINHTTP_NO_REFERER, WINHTTP_DEFAULT_ACCEPT_TYPES,
                                  dwFlags);
    if (!hRequest) {
        WinHttpCloseHandle(hConnect);
        WinHttpCloseHandle(hSession);
        return text;
    }

    if (opts_.ssl_bypass) {
        DWORD dwOptions = SECURITY_FLAG_IGNORE_UNKNOWN_CA | SECURITY_FLAG_IGNORE_CERT_CN_INVALID |
                          SECURITY_FLAG_IGNORE_CERT_DATE_INVALID | SECURITY_FLAG_IGNORE_CERT_WRONG_USAGE;
        WinHttpSetOption(hRequest, WINHTTP_OPTION_SECURITY_FLAGS, &dwOptions, sizeof(dwOptions));
    }

    // Headers
    std::wstring headers = L"Content-Type: application/json\r\n";
    std::string bearer = std::string("Authorization: Bearer ") + opts_.api_key + "\r\n";
    std::wstring wbearer(bearer.begin(), bearer.end());
    headers += wbearer;

    // Send request
    BOOL bResults = WinHttpSendRequest(hRequest,
                                       headers.c_str(), (DWORD)-1,
                                       (LPVOID)body_str.data(), (DWORD)body_str.size(),
                                       (DWORD)body_str.size(), 0);
    if (!bResults) {
        WinHttpCloseHandle(hRequest);
        WinHttpCloseHandle(hConnect);
        WinHttpCloseHandle(hSession);
        return text;
    }

    bResults = WinHttpReceiveResponse(hRequest, NULL);
    if (!bResults) {
        WinHttpCloseHandle(hRequest);
        WinHttpCloseHandle(hConnect);
        WinHttpCloseHandle(hSession);
        return text;
    }

    std::string response;
    DWORD dwSize = 0;
    do {
        dwSize = 0;
        if (!WinHttpQueryDataAvailable(hRequest, &dwSize)) break;
        if (dwSize == 0) break;

        std::string buffer;
        buffer.resize(dwSize);
        DWORD dwRead = 0;
        if (!WinHttpReadData(hRequest, &buffer[0], dwSize, &dwRead)) break;
        response.append(buffer.c_str(), dwRead);
    } while (dwSize > 0);

    // Try to extract translated content from JSON: choices[0].message.content
    try {
        std::smatch m;
        std::regex re("\\\"content\\\"\\s*:\\s*\\\"(.*?)\\\"");
        if (std::regex_search(response, m, re)) {
            std::string content = m[1].str();
            // Unescape common sequences
            std::string out;
            out.reserve(content.size());
            for (size_t i = 0; i < content.size(); ++i) {
                char c = content[i];
                if (c == '\\' && i + 1 < content.size()) {
                    char n = content[i + 1];
                    if (n == 'n') { out.push_back('\n'); ++i; }
                    else if (n == 'r') { out.push_back('\r'); ++i; }
                    else if (n == 't') { out.push_back('\t'); ++i; }
                    else if (n == '"') { out.push_back('"'); ++i; }
                    else if (n == '\\') { out.push_back('\\'); ++i; }
                    else { out.push_back(n); ++i; }
                } else {
                    out.push_back(c);
                }
            }
            result_text = out;
        }
    } catch (...) {
        // leave result_text as original text
    }

    WinHttpCloseHandle(hRequest);
    WinHttpCloseHandle(hConnect);
    WinHttpCloseHandle(hSession);
    return result_text;
#endif
}

TranslationResult OpenAITranslator::translate_segments(const std::vector<Segment>& segments,
                                                       const std::string& target_language,
                                                       const std::string& source_language) {
    TranslationResult result;
    result.source_language = source_language.empty() ? "auto" : source_language;
    result.target_language = target_language;
    result.translator_name = "openai";
    result.segments.reserve(segments.size());

    int retries = std::max(0, opts_.retry_count);

    for (const auto& seg : segments) {
        Segment tseg = seg;
        std::string translated;
        int attempt = 0;
        do {
            translated = translate_text(seg.text, target_language, result.source_language);
            if (!translated.empty()) break;
            attempt++;
            #ifdef _WIN32
            Sleep(200);
            #endif
        } while (attempt <= retries);
        if (!translated.empty()) {
            tseg.text = translated;
            tseg.language = target_language;
        } else {
            tseg.language = target_language;
        }
        result.segments.push_back(std::move(tseg));
    }

    return result;
}

} // namespace v2s