#include "video2srt_native/google_translator.hpp"
#include <windows.h>
#include <winhttp.h>
#include <string>
#include <vector>
#include <sstream>
#include <algorithm>
#include <iomanip>
#include <cctype>

#pragma comment(lib, "winhttp.lib")

namespace v2s {

static std::string url_encode(const std::string& value) {
    std::ostringstream escaped;
    escaped << std::uppercase << std::hex;
    for (unsigned char c : value) {
        if (std::isalnum(c) || c == '-' || c == '_' || c == '.' || c == '~') {
            escaped << c;
        } else {
            escaped << '%';
            escaped << std::setw(2) << std::setfill('0') << int(c);
        }
    }
    return escaped.str();
}

static std::string parse_google_response_first_string(const std::string& body) {
    // 简单解析：定位到 [[["xxx" 的第一个字符串
    size_t pos = body.find("[[[");
    if (pos == std::string::npos) return {};
    pos = body.find('"', pos);
    if (pos == std::string::npos) return {};
    size_t end = pos + 1;
    std::string out;
    while (end < body.size()) {
        char ch = body[end++];
        if (ch == '\\') {
            if (end < body.size()) {
                char next = body[end++];
                if (next == 'n') out += '\n';
                else if (next == 'r') out += '\r';
                else out += next;
            }
        } else if (ch == '"') {
            break;
        } else {
            out += ch;
        }
    }
    return out;
}

GoogleTranslator::GoogleTranslator(const TranslatorOptions& opts) : opts_(opts) {}

std::string GoogleTranslator::translate_text(const std::string& text,
                                             const std::string& target_language,
                                             const std::string& source_language) {
    // 构造URL
    std::wstring host = L"translate.googleapis.com";
    std::ostringstream path_qs;
    path_qs << "/translate_a/single?client=gtx&sl=" << source_language
            << "&tl=" << target_language << "&dt=t&q=" << url_encode(text);
    std::string path_qs_utf8 = path_qs.str();
    std::wstring path;
    path.assign(path_qs_utf8.begin(), path_qs_utf8.end());

    HINTERNET hSession = WinHttpOpen(L"Video2SRT-Native/1.0",
                                     WINHTTP_ACCESS_TYPE_DEFAULT_PROXY,
                                     WINHTTP_NO_PROXY_NAME,
                                     WINHTTP_NO_PROXY_BYPASS, 0);
    if (!hSession) return {};

    // 设置超时
    if (opts_.timeout_seconds > 0) {
        int ms = opts_.timeout_seconds * 1000;
        WinHttpSetTimeouts(hSession, ms, ms, ms, ms);
    }

    HINTERNET hConnect = WinHttpConnect(hSession, host.c_str(), INTERNET_DEFAULT_HTTPS_PORT, 0);
    if (!hConnect) { WinHttpCloseHandle(hSession); return {}; }

    HINTERNET hRequest = WinHttpOpenRequest(hConnect, L"GET", path.c_str(),
                                            NULL, WINHTTP_NO_REFERER,
                                            WINHTTP_DEFAULT_ACCEPT_TYPES,
                                            WINHTTP_FLAG_SECURE);
    if (!hRequest) { WinHttpCloseHandle(hConnect); WinHttpCloseHandle(hSession); return {}; }

    if (opts_.ssl_bypass) {
        DWORD flags = SECURITY_FLAG_IGNORE_UNKNOWN_CA | SECURITY_FLAG_IGNORE_CERT_CN_INVALID |
                     SECURITY_FLAG_IGNORE_CERT_DATE_INVALID | SECURITY_FLAG_IGNORE_CERT_WRONG_USAGE;
        WinHttpSetOption(hRequest, WINHTTP_OPTION_SECURITY_FLAGS, &flags, sizeof(flags));
    }

    std::string result_body;
    for (int attempt = 0; attempt <= std::max(0, opts_.retry_count); ++attempt) {
        BOOL ok = WinHttpSendRequest(hRequest, WINHTTP_NO_ADDITIONAL_HEADERS, 0,
                                     WINHTTP_NO_REQUEST_DATA, 0, 0, 0);
        if (!ok) {
            continue;
        }
        ok = WinHttpReceiveResponse(hRequest, NULL);
        if (!ok) {
            continue;
        }
        DWORD dwSize = 0;
        do {
            dwSize = 0;
            if (!WinHttpQueryDataAvailable(hRequest, &dwSize)) break;
            if (dwSize == 0) break;
            std::string buffer;
            buffer.resize(dwSize);
            DWORD dwDownloaded = 0;
            if (!WinHttpReadData(hRequest, &buffer[0], dwSize, &dwDownloaded)) break;
            buffer.resize(dwDownloaded);
            result_body += buffer;
        } while (dwSize > 0);

        if (!result_body.empty()) break; // 成功
        // 失败则重试
        Sleep(200);
    }

    if (hRequest) WinHttpCloseHandle(hRequest);
    if (hConnect) WinHttpCloseHandle(hConnect);
    if (hSession) WinHttpCloseHandle(hSession);

    if (result_body.empty()) return {};
    return parse_google_response_first_string(result_body);
}

TranslationResult GoogleTranslator::translate_segments(const std::vector<Segment>& segments,
                                                       const std::string& target_language,
                                                       const std::string& source_language) {
    TranslationResult result;
    result.source_language = source_language.empty() ? "auto" : source_language;
    result.target_language = target_language;
    result.translator_name = "google";

    result.segments.reserve(segments.size());
    for (const auto& seg : segments) {
        Segment tseg = seg;
        std::string translated = translate_text(seg.text, target_language, result.source_language);
        if (!translated.empty()) {
            tseg.text = translated;
            tseg.language = target_language;
        } else {
            // 如果失败，保留原文以保证管线不中断
            tseg.language = target_language;
        }
        result.segments.push_back(std::move(tseg));
    }
    return result;
}

} // namespace v2s