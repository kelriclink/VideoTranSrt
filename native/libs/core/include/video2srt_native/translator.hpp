#pragma once

#include "models.hpp"
#include <string>
#include <vector>
#include <memory>

namespace v2s {

/**
 * 翻译器基础接口
 * 提供统一的字幕段翻译能力
 */
class ITranslator {
public:
    virtual ~ITranslator() = default;

    /**
     * 翻译字幕段列表
     * @param segments 原始字幕段
     * @param target_language 目标语言代码
     * @param source_language 源语言代码（可为"auto"或空）
     * @return 翻译结果
     */
    virtual TranslationResult translate_segments(const std::vector<Segment>& segments,
                                                 const std::string& target_language,
                                                 const std::string& source_language = "auto") = 0;
};

/**
 * 简单翻译器占位实现
 * 当前版本不进行真实翻译，仅复制原文，用于打通C++管线
 */
class SimpleTranslator : public ITranslator {
public:
    TranslationResult translate_segments(const std::vector<Segment>& segments,
                                         const std::string& target_language,
                                         const std::string& source_language = "auto") override;
};

/**
 * 翻译器工厂函数
 * 根据类型返回对应翻译器实例
 */
std::unique_ptr<ITranslator> create_translator(const std::string& translator_type,
                                               const TranslatorOptions& opts = TranslatorOptions{});

} // namespace v2s