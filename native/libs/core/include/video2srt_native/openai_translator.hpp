#pragma once

#include "translator.hpp"
#include "models.hpp"

namespace v2s {

/**
 * OpenAI 翻译器实现（使用 WinHTTP 调用 Chat Completions）
 * 读取 TranslatorOptions 中的 api_key/base_url/model/max_tokens/temperature 等参数
 */
class OpenAITranslator : public ITranslator {
public:
    explicit OpenAITranslator(const TranslatorOptions& opts);

    TranslationResult translate_segments(const std::vector<Segment>& segments,
                                         const std::string& target_language,
                                         const std::string& source_language = "auto") override;

private:
    TranslatorOptions opts_;

    std::string translate_text(const std::string& text,
                               const std::string& target_language,
                               const std::string& source_language);
};

} // namespace v2s