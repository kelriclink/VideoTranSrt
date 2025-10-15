#include "video2srt_native/translator.hpp"
#include "video2srt_native/google_translator.hpp"
#include "video2srt_native/openai_translator.hpp"
#include <memory>

namespace v2s {

TranslationResult SimpleTranslator::translate_segments(const std::vector<Segment>& segments,
                                                       const std::string& target_language,
                                                       const std::string& source_language) {
    TranslationResult result;
    result.source_language = source_language.empty() ? "auto" : source_language;
    result.target_language = target_language;
    result.translator_name = "simple";

    // 占位实现：直接复制原文内容
    result.segments.reserve(segments.size());
    for (const auto& seg : segments) {
        Segment tseg = seg;
        tseg.language = target_language;
        // 这里可以在后续替换为真实翻译文本
        tseg.text = seg.text; 
        result.segments.push_back(std::move(tseg));
    }

    return result;
}

std::unique_ptr<ITranslator> create_translator(const std::string& translator_type,
                                               const TranslatorOptions& opts) {
    // 简单工厂：目前支持 simple、google（仅Windows）、openai
    if (translator_type == "google") {
#ifdef _WIN32
        return std::make_unique<GoogleTranslator>(opts);
#else
        // 非 Windows 平台尚未实现 GoogleTranslator，退化为简单译者（保持兼容）
        return std::make_unique<SimpleTranslator>();
#endif
    }
    if (translator_type == "openai") {
        return std::make_unique<OpenAITranslator>(opts);
    }
    return std::make_unique<SimpleTranslator>();
}

} // namespace v2s