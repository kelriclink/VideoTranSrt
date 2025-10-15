#pragma once

#include "translator.hpp"
#include "models.hpp"

namespace v2s {

/**
 * Google 翻译器实现（使用 WinHTTP 发起请求）
 * 注意：使用的是非官方端点 translate.googleapis.com
 */
class GoogleTranslator : public ITranslator {
public:
    explicit GoogleTranslator(const TranslatorOptions& opts);

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