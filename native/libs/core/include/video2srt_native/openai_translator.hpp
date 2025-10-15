#pragma once

#include <string>
#include <vector>
#include "video2srt_native/models.hpp"
#include "video2srt_native/translator.hpp"

namespace v2s {

class OpenAITranslator : public ITranslator {
public:
    explicit OpenAITranslator(const TranslatorOptions& opts);

    TranslationResult translate_segments(const std::vector<Segment>& segments,
                                         const std::string& target_language,
                                         const std::string& source_language) override;

private:
    TranslatorOptions opts_;

    // Translate a single text string
    std::string translate_text(const std::string& text,
                               const std::string& target_language,
                               const std::string& source_language);

    // Translate multiple text strings in one request
    std::vector<std::string> translate_texts_batch(const std::vector<std::string>& texts,
                                                   const std::string& target_language,
                                                   const std::string& source_language);
};

} // namespace v2s