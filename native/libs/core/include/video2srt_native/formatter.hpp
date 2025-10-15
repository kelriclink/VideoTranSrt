#pragma once

#include "models.hpp"
#include <string>
#include <vector>
#include <filesystem>

namespace v2s {

/**
 * SRT字幕格式化器
 * 将转录结果转换为标准SRT字幕格式
 */
class SRTFormatter {
public:
    /**
     * 格式化单个字幕段
     * @param segment 字幕段数据
     * @param index 字幕段序号（从1开始）
     * @return 格式化的字幕段字符串
     */
    static std::string format_segment(const Segment& segment, int index);
    
    /**
     * 格式化所有字幕段
     * @param segments 字幕段列表
     * @param min_duration 最小持续时间（秒），用于修正过短的段
     * @return 完整的SRT格式字符串
     */
    static std::string format_segments(const std::vector<Segment>& segments, 
                                     double min_duration = 0.5);
    
    /**
     * 保存SRT内容到文件
     * @param content SRT格式内容
     * @param output_path 输出文件路径
     * @return 是否保存成功
     */
    static bool save_srt(const std::string& content, 
                        const std::filesystem::path& output_path);
    
    /**
     * 创建双语字幕
     * @param original_segments 原始字幕段
     * @param translated_segments 翻译字幕段
     * @return 双语SRT格式字符串
     */
    static std::string create_bilingual_srt(const std::vector<Segment>& original_segments,
                                          const std::vector<Segment>& translated_segments);
    
    /**
     * 合并过短的字幕段
     * @param segments 字幕段列表
     * @param min_duration 最小持续时间（秒）
     * @return 合并后的字幕段列表
     */
    static std::vector<Segment> merge_short_segments(const std::vector<Segment>& segments,
                                                   double min_duration = 1.0);

private:
    /**
     * 修正字幕段的时间，确保时间合法性
     * @param segments 输入的字幕段列表
     * @param min_duration 最小持续时间
     * @return 修正后的字幕段列表
     */
    static std::vector<Segment> fix_segment_timing(const std::vector<Segment>& segments,
                                                 double min_duration);
};

} // namespace v2s