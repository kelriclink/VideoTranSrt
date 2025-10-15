#include "video2srt_native/formatter.hpp"
#include <sstream>
#include <iomanip>
#include <fstream>
#include <algorithm>

namespace v2s {

std::string SRTFormatter::format_segment(const Segment& segment, int index) {
    std::string start_time = format_srt_time(segment.start);
    std::string end_time = format_srt_time(segment.end);
    
    // 清理文本，移除首尾空白
    std::string text = segment.text;
    // 简单的trim实现
    text.erase(text.begin(), std::find_if(text.begin(), text.end(), [](unsigned char ch) {
        return !std::isspace(ch);
    }));
    text.erase(std::find_if(text.rbegin(), text.rend(), [](unsigned char ch) {
        return !std::isspace(ch);
    }).base(), text.end());
    
    std::ostringstream oss;
    oss << index << "\n"
        << start_time << " --> " << end_time << "\n"
        << text << "\n";
    
    return oss.str();
}

std::string SRTFormatter::format_segments(const std::vector<Segment>& segments, 
                                        double min_duration) {
    if (segments.empty()) {
        return "";
    }
    
    // 修正时间并过滤空文本
    std::vector<Segment> fixed_segments = fix_segment_timing(segments, min_duration);
    
    std::ostringstream srt_content;
    for (size_t i = 0; i < fixed_segments.size(); ++i) {
        srt_content << format_segment(fixed_segments[i], static_cast<int>(i + 1));
        if (i < fixed_segments.size() - 1) {
            srt_content << "\n";
        }
    }
    
    return srt_content.str();
}

bool SRTFormatter::save_srt(const std::string& content, 
                          const std::filesystem::path& output_path) {
    try {
        // 确保输出目录存在
        std::filesystem::create_directories(output_path.parent_path());
        
        // 保存文件，使用UTF-8编码
        std::ofstream file(output_path, std::ios::out | std::ios::trunc);
        if (!file.is_open()) {
            return false;
        }
        
        file << content;
        file.close();
        
        return true;
    } catch (const std::exception&) {
        return false;
    }
}

std::string SRTFormatter::create_bilingual_srt(const std::vector<Segment>& original_segments,
                                             const std::vector<Segment>& translated_segments) {
    if (original_segments.size() != translated_segments.size()) {
        // 如果段数不匹配，只使用原始字幕
        return format_segments(original_segments);
    }
    
    std::vector<Segment> bilingual_segments;
    bilingual_segments.reserve(original_segments.size());
    
    for (size_t i = 0; i < original_segments.size(); ++i) {
        const Segment& orig = original_segments[i];
        const Segment& trans = translated_segments[i];
        
        // 创建双语段：原文 + 翻译
        Segment bilingual_seg = orig;  // 复制时间信息
        bilingual_seg.text = orig.text + "\n" + trans.text;
        
        bilingual_segments.push_back(bilingual_seg);
    }
    
    return format_segments(bilingual_segments);
}

std::vector<Segment> SRTFormatter::merge_short_segments(const std::vector<Segment>& segments,
                                                      double min_duration) {
    if (segments.empty()) {
        return segments;
    }
    
    std::vector<Segment> merged;
    merged.reserve(segments.size());
    
    Segment current_segment = segments[0];
    
    for (size_t i = 1; i < segments.size(); ++i) {
        const Segment& next_segment = segments[i];
        
        // 如果当前段太短，尝试与下一段合并
        double current_duration = current_segment.end - current_segment.start;
        if (current_duration < min_duration) {
            // 合并文本和时间
            current_segment.text += " " + next_segment.text;
            current_segment.end = next_segment.end;
            
            // 合并其他属性
            if (!current_segment.language.has_value() && next_segment.language.has_value()) {
                current_segment.language = next_segment.language;
            }
            
            if (current_segment.confidence.has_value() && next_segment.confidence.has_value()) {
                current_segment.confidence = (current_segment.confidence.value() + 
                                            next_segment.confidence.value()) / 2.0;
            } else if (!current_segment.confidence.has_value() && next_segment.confidence.has_value()) {
                current_segment.confidence = next_segment.confidence;
            }
        } else {
            // 当前段足够长，添加到结果中
            merged.push_back(current_segment);
            current_segment = next_segment;
        }
    }
    
    // 添加最后一个段
    merged.push_back(current_segment);
    
    return merged;
}

std::vector<Segment> SRTFormatter::fix_segment_timing(const std::vector<Segment>& segments,
                                                    double min_duration) {
    std::vector<Segment> fixed_segments;
    fixed_segments.reserve(segments.size());
    
    // 过滤空文本段并规范化
    for (const Segment& seg : segments) {
        // 跳过空文本
        std::string trimmed_text = seg.text;
        trimmed_text.erase(trimmed_text.begin(), std::find_if(trimmed_text.begin(), trimmed_text.end(), [](unsigned char ch) {
            return !std::isspace(ch);
        }));
        trimmed_text.erase(std::find_if(trimmed_text.rbegin(), trimmed_text.rend(), [](unsigned char ch) {
            return !std::isspace(ch);
        }).base(), trimmed_text.end());
        
        if (trimmed_text.empty()) {
            continue;
        }
        
        Segment normalized_seg = seg;
        normalized_seg.text = trimmed_text;
        
        // 修正负时间
        if (normalized_seg.start < 0) {
            normalized_seg.start = 0.0;
        }
        if (normalized_seg.end < 0) {
            normalized_seg.end = 0.0;
        }
        
        fixed_segments.push_back(normalized_seg);
    }
    
    // 按开始时间排序
    std::sort(fixed_segments.begin(), fixed_segments.end(), 
              [](const Segment& a, const Segment& b) {
                  return a.start < b.start;
              });
    
    // 修正时间重叠和过短问题
    double last_end = 0.0;
    for (Segment& seg : fixed_segments) {
        // 修正开始时间重叠
        if (seg.start < last_end) {
            seg.start = last_end;
        }
        
        // 修正结束时间
        if (seg.end <= seg.start) {
            seg.end = seg.start + min_duration;
        }
        
        // 确保最小持续时间
        if ((seg.end - seg.start) < min_duration) {
            seg.end = seg.start + min_duration;
        }
        
        last_end = seg.end;
    }
    
    return fixed_segments;
}

} // namespace v2s