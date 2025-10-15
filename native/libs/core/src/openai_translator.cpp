// Cross-platform OpenAI translator implementation
// - Windows: WinHTTP
// - Non-Windows: libcurl (if available)

#include "video2srt_native/openai_translator.hpp"
#include "video2srt_native/models.hpp"
#include <string>
#include <vector>
#include <optional>
#include <sstream>
#include <algorithm>
#include <chrono>
#include <thread>

#include <nlohmann/json.hpp>

#ifdef _WIN32
#include <windows.h>
#include <winhttp.h>
#pragma comment(lib, "winhttp.lib")
#endif

#ifdef V2S_HAVE_LIBCURL
#include <curl/curl.h>
#endif

namespace v2s {

namespace {

// Remove leading/trailing whitespace
static std::string trim(const std::string& s) {
    auto start = s.find_first_not_of("\r\n\t ");
    auto end = s.find_last_not_of("\r\n\t ");
    if (start == std::string::npos) return "";
    return s.substr(start, end - start + 1);
}

// Strip Markdown code fences if present
static std::string strip_code_fences(const std::string& content) {
    std::string c = trim(content);
    if (c.size() >= 6 && c.rfind("```", std::string::npos) != std::string::npos && c.find("```") == 0) {
        // Remove starting ```lang?
        size_t first_newline = c.find('\n');
        if (first_newline != std::string::npos) {
            c = c.substr(first_newline + 1);
        }
        // Remove trailing ```
        size_t last_fence = c.rfind("```");
        if (last_fence != std::string::npos) {
            c = c.substr(0, last_fence);
        }
    }
    return trim(c);
}

// Build the chat completion request body for single-text translation
static std::string build_chat_body_single(const TranslatorOptions& opts,
                                          const std::string& text,
                                          const std::string& target_lang,
                                          const std::string& source_lang) {
    std::string system_prompt = "You are a professional translator. Translate the user's text";
    if (!source_lang.empty()) system_prompt += " from " + source_lang;
    if (!target_lang.empty()) system_prompt += " to " + target_lang;
    system_prompt += ". Return only the translated text without explanations.";

    nlohmann::json j;
    j["model"] = opts.model.empty() ? "gpt-4o-mini" : opts.model;
    j["temperature"] = opts.temperature;
    j["max_tokens"] = opts.max_tokens;
    j["messages"] = nlohmann::json::array({
        nlohmann::json{{"role","system"},{"content",system_prompt}},
        nlohmann::json{{"role","user"},{"content",text}}
    });
    return j.dump();
}

// Build the chat completion request body for batch translation
static std::string build_chat_body_batch(const TranslatorOptions& opts,
                                         const std::vector<std::string>& texts,
                                         const std::string& target_lang,
                                         const std::string& source_lang) {
    std::string system_prompt = "You are a professional translator. Translate the provided array of text segments";
    if (!source_lang.empty()) system_prompt += " from " + source_lang;
    if (!target_lang.empty()) system_prompt += " to " + target_lang;
    system_prompt += ". Return ONLY a compact JSON object with a single key 'translations' whose value is an array of strings of the same length and order as the input. Do not include any extra words, explanations, or keys.";

    nlohmann::json texts_json = nlohmann::json::array();
    for (const auto& t : texts) {
        texts_json.push_back(t);
    }
    std::string user_content = texts_json.dump();

    nlohmann::json j;
    j["model"] = opts.model.empty() ? "gpt-4o-mini" : opts.model;
    j["temperature"] = opts.temperature;
    j["max_tokens"] = opts.max_tokens;
    j["messages"] = nlohmann::json::array({
        nlohmann::json{{"role","system"},{"content",system_prompt}},
        nlohmann::json{{"role","user"},{"content",user_content}}
    });
    if (opts.structured_json_output) {
        // Hint to return valid JSON (OpenAI supports response_format JSON for some models)
        j["response_format"] = nlohmann::json{{"type","json_object"}};
    }
    return j.dump();
}

#ifdef _WIN32
struct ParsedUrl {
    bool secure = true;
    std::wstring host;
    INTERNET_PORT port = 443;
    std::wstring path;
};

static ParsedUrl parse_url_w(const std::string& url) {
    ParsedUrl out;
    // very simple parse
    std::string u = url;
    if (u.rfind("https://", 0) == 0) {
        out.secure = true;
        u = u.substr(8);
        out.port = 443;
    } else if (u.rfind("http://", 0) == 0) {
        out.secure = false;
        u = u.substr(7);
        out.port = 80;
    }
    size_t slash = u.find('/');
    std::string host = (slash == std::string::npos) ? u : u.substr(0, slash);
    std::string path = (slash == std::string::npos) ? "/" : u.substr(slash);
    size_t colon = host.find(':');
    if (colon != std::string::npos) {
        out.port = static_cast<INTERNET_PORT>(std::stoi(host.substr(colon+1)));
        host = host.substr(0, colon);
    }
    out.host = std::wstring(host.begin(), host.end());
    out.path = std::wstring(path.begin(), path.end());
    return out;
}

static std::optional<std::string> http_post_winhttp(const std::string& url,
                                                    const std::string& body,
                                                    const std::vector<std::pair<std::string,std::string>>& headers,
                                                    int timeout_seconds,
                                                    bool ssl_bypass) {
    auto pu = parse_url_w(url);
    HINTERNET hSession = WinHttpOpen(L"Video2SRT/1.0",
                                     WINHTTP_ACCESS_TYPE_DEFAULT_PROXY,
                                     WINHTTP_NO_PROXY_NAME,
                                     WINHTTP_NO_PROXY_BYPASS, 0);
    if (!hSession) return std::nullopt;

    // timeouts
    DWORD t = static_cast<DWORD>(timeout_seconds * 1000);
    WinHttpSetTimeouts(hSession, t, t, t, t);

    HINTERNET hConnect = WinHttpConnect(hSession, pu.host.c_str(), pu.port, 0);
    if (!hConnect) { WinHttpCloseHandle(hSession); return std::nullopt; }

    HINTERNET hRequest = WinHttpOpenRequest(hConnect, L"POST", pu.path.c_str(),
                                            NULL, WINHTTP_NO_REFERER,
                                            WINHTTP_DEFAULT_ACCEPT_TYPES,
                                            pu.secure ? WINHTTP_FLAG_SECURE : 0);
    if (!hRequest) {
        WinHttpCloseHandle(hConnect);
        WinHttpCloseHandle(hSession);
        return std::nullopt;
    }

    if (ssl_bypass) {
        DWORD flags = SECURITY_FLAG_IGNORE_UNKNOWN_CA |
                      SECURITY_FLAG_IGNORE_CERT_CN_INVALID |
                      SECURITY_FLAG_IGNORE_CERT_DATE_INVALID |
                      SECURITY_FLAG_IGNORE_CERT_WRONG_USAGE;
        WinHttpSetOption(hRequest, WINHTTP_OPTION_SECURITY_FLAGS, &flags, sizeof(flags));
    }

    std::wstring hdrs;
    for (const auto& kv : headers) {
        std::wstring k(kv.first.begin(), kv.first.end());
        std::wstring v(kv.second.begin(), kv.second.end());
        hdrs += k + L": " + v + L"\r\n";
    }

    BOOL sent = WinHttpSendRequest(hRequest,
                                   hdrs.c_str(), (DWORD)hdrs.size(),
                                   (LPVOID)body.data(), (DWORD)body.size(), (DWORD)body.size(), 0);
    if (!sent) {
        WinHttpCloseHandle(hRequest);
        WinHttpCloseHandle(hConnect);
        WinHttpCloseHandle(hSession);
        return std::nullopt;
    }

    BOOL res = WinHttpReceiveResponse(hRequest, NULL);
    if (!res) {
        WinHttpCloseHandle(hRequest);
        WinHttpCloseHandle(hConnect);
        WinHttpCloseHandle(hSession);
        return std::nullopt;
    }

    std::string response;
    DWORD dwSize = 0;
    do {
        dwSize = 0;
        if (!WinHttpQueryDataAvailable(hRequest, &dwSize)) break;
        if (dwSize == 0) break;
        std::string buf;
        buf.resize(dwSize);
        DWORD dwDownloaded = 0;
        if (!WinHttpReadData(hRequest, &buf[0], dwSize, &dwDownloaded)) break;
        response.append(buf.data(), dwDownloaded);
    } while (dwSize > 0);

    WinHttpCloseHandle(hRequest);
    WinHttpCloseHandle(hConnect);
    WinHttpCloseHandle(hSession);
    return response.empty() ? std::nullopt : std::optional<std::string>(response);
}
#endif // _WIN32

#ifdef V2S_HAVE_LIBCURL
static size_t curl_write_cb(char* ptr, size_t size, size_t nmemb, void* userdata) {
    auto* out = reinterpret_cast<std::string*>(userdata);
    out->append(ptr, size * nmemb);
    return size * nmemb;
}

static std::optional<std::string> http_post_curl(const std::string& url,
                                                 const std::string& body,
                                                 const std::vector<std::pair<std::string,std::string>>& headers,
                                                 int timeout_seconds,
                                                 bool ssl_bypass) {
    CURL* curl = curl_easy_init();
    if (!curl) return std::nullopt;
    std::string response;
    curl_easy_setopt(curl, CURLOPT_URL, url.c_str());
    curl_easy_setopt(curl, CURLOPT_POST, 1L);
    curl_easy_setopt(curl, CURLOPT_POSTFIELDS, body.c_str());
    curl_easy_setopt(curl, CURLOPT_WRITEFUNCTION, curl_write_cb);
    curl_easy_setopt(curl, CURLOPT_WRITEDATA, &response);
    curl_easy_setopt(curl, CURLOPT_TIMEOUT, timeout_seconds);
    curl_easy_setopt(curl, CURLOPT_CONNECTTIMEOUT, timeout_seconds);
    if (ssl_bypass) {
        curl_easy_setopt(curl, CURLOPT_SSL_VERIFYPEER, 0L);
        curl_easy_setopt(curl, CURLOPT_SSL_VERIFYHOST, 0L);
    }
    struct curl_slist* hdr = nullptr;
    for (const auto& kv : headers) {
        std::string h = kv.first + ": " + kv.second;
        hdr = curl_slist_append(hdr, h.c_str());
    }
    if (hdr) curl_easy_setopt(curl, CURLOPT_HTTPHEADER, hdr);
    CURLcode rc = curl_easy_perform(curl);
    long http_code = 0;
    curl_easy_getinfo(curl, CURLINFO_RESPONSE_CODE, &http_code);
    if (hdr) curl_slist_free_all(hdr);
    curl_easy_cleanup(curl);
    if (rc != CURLE_OK) return std::nullopt;
    if (http_code < 200 || http_code >= 300) return std::nullopt;
    return response.empty() ? std::nullopt : std::optional<std::string>(response);
}
#endif // V2S_HAVE_LIBCURL

static std::optional<std::string> http_post_any(const std::string& url,
                                                const std::string& body,
                                                const std::vector<std::pair<std::string,std::string>>& headers,
                                                int timeout_seconds,
                                                bool ssl_bypass) {
#ifdef _WIN32
    return http_post_winhttp(url, body, headers, timeout_seconds, ssl_bypass);
#elif defined(V2S_HAVE_LIBCURL)
    return http_post_curl(url, body, headers, timeout_seconds, ssl_bypass);
#else
    (void)url; (void)body; (void)headers; (void)timeout_seconds; (void)ssl_bypass;
    return std::nullopt;
#endif
}

} // namespace

OpenAITranslator::OpenAITranslator(const TranslatorOptions& opts) : opts_(opts) {}

static std::string default_base_url() {
    return "https://api.openai.com/v1/chat/completions";
}

// Single-text translation with retries and JSON parsing
std::string OpenAITranslator::translate_text(const std::string& text,
                                             const std::string& target_language,
                                             const std::string& source_language) {
    const std::string url = opts_.base_url.empty() ? default_base_url() : opts_.base_url;
    const std::string body = build_chat_body_single(opts_, text, target_language, source_language);
    std::vector<std::pair<std::string,std::string>> headers = {
        {"Content-Type","application/json"},
        {"Authorization","Bearer " + opts_.api_key}
    };

    for (int attempt = 0; attempt <= std::max(0, opts_.retry_count); ++attempt) {
        auto resp = http_post_any(url, body, headers, opts_.timeout_seconds, opts_.ssl_bypass);
        if (resp) {
            try {
                auto j = nlohmann::json::parse(*resp);
                if (j.contains("choices") && j["choices"].is_array() && !j["choices"].empty()) {
                    const auto& msg = j["choices"][0]["message"]["content"];
                    if (!msg.is_null()) {
                        return trim(msg.get<std::string>());
                    }
                }
            } catch (...) {
                // fallthrough to retry
            }
        }
        if (attempt < opts_.retry_count) {
#ifdef _WIN32
            Sleep(500);
#else
            std::this_thread::sleep_for(std::chrono::milliseconds(500));
#endif
        }
    }
    // Fallback: return original text
    return text;
}

// Batch translation returning array of translated strings
std::vector<std::string> OpenAITranslator::translate_texts_batch(const std::vector<std::string>& texts,
                                                                 const std::string& target_language,
                                                                 const std::string& source_language) {
    const std::string url = opts_.base_url.empty() ? default_base_url() : opts_.base_url;
    const std::string body = build_chat_body_batch(opts_, texts, target_language, source_language);
    std::vector<std::pair<std::string,std::string>> headers = {
        {"Content-Type","application/json"},
        {"Authorization","Bearer " + opts_.api_key}
    };

    for (int attempt = 0; attempt <= std::max(0, opts_.retry_count); ++attempt) {
        auto resp = http_post_any(url, body, headers, opts_.timeout_seconds, opts_.ssl_bypass);
        if (resp) {
            try {
                auto j = nlohmann::json::parse(*resp);
                std::string content;
                if (j.contains("choices") && j["choices"].is_array() && !j["choices"].empty()) {
                    const auto& msg = j["choices"][0]["message"]["content"];
                    if (!msg.is_null()) {
                        content = msg.get<std::string>();
                    }
                }
                content = strip_code_fences(content);
                auto j2 = nlohmann::json::parse(content);
                std::vector<std::string> out;
                if (j2.contains("translations") && j2["translations"].is_array()) {
                    for (const auto& item : j2["translations"]) {
                        out.push_back(item.get<std::string>());
                    }
                }
                if (!out.empty()) return out;
            } catch (...) {
                // fallthrough to retry
            }
        }
        if (attempt < opts_.retry_count) {
#ifdef _WIN32
            Sleep(500);
#else
            std::this_thread::sleep_for(std::chrono::milliseconds(500));
#endif
        }
    }
    // Fallback: return original texts
    return texts;
}

// Helper to group segments by total char length and max count
static std::vector<std::vector<size_t>> group_indices_by_limits(const std::vector<Segment>& segs, size_t max_chars, int max_segments) {
    std::vector<std::vector<size_t>> groups;
    std::vector<size_t> current;
    size_t char_count = 0;
    for (size_t i = 0; i < segs.size(); ++i) {
        const auto& s = segs[i];
        size_t len = s.text.size();
        if (!current.empty() && ((char_count + len) > max_chars || (int)current.size() >= max_segments)) {
            groups.push_back(current);
            current.clear();
            char_count = 0;
        }
        current.push_back(i);
        char_count += len;
    }
    if (!current.empty()) groups.push_back(current);
    return groups;
}

TranslationResult OpenAITranslator::translate_segments(const std::vector<Segment>& segments,
                                                       const std::string& target_language,
                                                       const std::string& source_language) {
    TranslationResult result;
    result.target_language = target_language;
    result.source_language = source_language;
    result.segments.reserve(segments.size());

    if (!opts_.batch_mode) {
        // per-segment translation
        for (const auto& seg : segments) {
            std::string translated = translate_text(seg.text, target_language, source_language);
            Segment out = seg;
            out.text = translated;
            result.segments.push_back(std::move(out));
        }
        return result;
    }

    // aggregated translation
    auto groups = group_indices_by_limits(segments, opts_.max_batch_chars, std::max(1, opts_.max_batch_segments));
    result.segments.resize(segments.size());

    for (const auto& group : groups) {
        std::vector<std::string> texts;
        texts.reserve(group.size());
        for (size_t idx : group) texts.push_back(segments[idx].text);
        auto translated_list = translate_texts_batch(texts, target_language, source_language);
        // map back
        for (size_t i = 0; i < group.size(); ++i) {
            size_t idx = group[i];
            Segment out = segments[idx];
            out.text = (i < translated_list.size()) ? translated_list[i] : segments[idx].text;
            result.segments[idx] = std::move(out);
        }
    }

    return result;
}

} // namespace v2s