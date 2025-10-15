#pragma once

#include "models.hpp"
#include <string>
#include <vector>
#include <filesystem>

namespace v2s {

/**
 * WebVTT 字幕格式化器
 */
class WebVTTFormatter {
public:
    /**
     * 格式化全部字幕段为WebVTT
     * @param segments 字幕段列表
     * @param min_duration 最小持续时间（秒）
     * @return 完整的WebVTT内容
     */
    static std::string format_segments(const std::vector<Segment>& segments,
                                       double min_duration = 0.5);

    /**
     * 保存为.vtt文件
     */
    static bool save_vtt(const std::string& content,
                         const std::filesystem::path& output_path);

    /**
     * 创建双语WebVTT内容
     */
    static std::string create_bilingual_vtt(const std::vector<Segment>& original_segments,
                                            const std::vector<Segment>& translated_segments);

private:
    static std::string format_vtt_time(double seconds);
};

} // namespace v2s

#pragma once

#include "models.hpp"
#include <string>
#include <vector>
#include <filesystem>

namespace v2s {

/**
 * ASS 字幕格式化器
 */
class ASSFormatter {
public:
    /**
     * 格式化全部字幕段为ASS
     * @param segments 字幕段列表
     * @param style 样式配置
     * @param min_duration 最小持续时间（秒）
     * @return 完整的ASS内容
     */
    static std::string format_segments(const std::vector<Segment>& segments,
                                       const ASSStyleConfig& style,
                                       double min_duration = 0.5);

    /**
     * 保存为.ass文件
     */
    static bool save_ass(const std::string& content,
                         const std::filesystem::path& output_path);

    /**
     * 创建双语ASS内容（原文+译文）
     */
    static std::string create_bilingual_ass(const std::vector<Segment>& original_segments,
                                            const std::vector<Segment>& translated_segments,
                                            const ASSStyleConfig& style,
                                            double min_duration = 0.5);

private:
    static std::string format_ass_time(double seconds);
};

} // namespace v2s