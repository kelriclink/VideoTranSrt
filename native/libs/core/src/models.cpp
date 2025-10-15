#include "video2srt_native/models.hpp"
#include <sstream>
#include <iomanip>
#include <algorithm>

namespace v2s {

std::vector<Segment> merge_segments(const std::vector<Segment>& segments, 
                                   double max_duration, 
                                   size_t max_chars) {
    if (segments.empty()) {
        return {};
    }
    
    std::vector<Segment> merged;
    Segment current = segments[0];
    
    for (size_t i = 1; i < segments.size(); ++i) {
        const Segment& next_seg = segments[i];
        
        // 检查是否可以合并
        double combined_duration = next_seg.end - current.start;
        std::string combined_text = current.text + " " + next_seg.text;
        double gap = next_seg.start - current.end;
        
        if (combined_duration <= max_duration && 
            combined_text.length() <= max_chars &&
            gap <= 2.0) {  // 间隔不超过2秒
            
            // 合并段
            current.end = next_seg.end;
            current.text = combined_text;
            
            // 保持语言信息（优先使用有值的）
            if (!current.language.has_value() && next_seg.language.has_value()) {
                current.language = next_seg.language;
            }
            
            // 置信度取平均值
            if (current.confidence.has_value() && next_seg.confidence.has_value()) {
                current.confidence = (current.confidence.value() + next_seg.confidence.value()) / 2.0;
            } else if (!current.confidence.has_value() && next_seg.confidence.has_value()) {
                current.confidence = next_seg.confidence;
            }
        } else {
            // 不能合并，保存当前段并开始新段
            merged.push_back(current);
            current = next_seg;
        }
    }
    
    // 添加最后一段
    merged.push_back(current);
    return merged;
}

bool validate_segments(const std::vector<Segment>& segments) {
    if (segments.empty()) {
        return true;  // 空列表是有效的
    }
    
    for (size_t i = 0; i < segments.size(); ++i) {
        const Segment& seg = segments[i];
        
        // 检查单个段的有效性
        if (!seg.is_valid()) {
            return false;
        }
        
        // 检查段之间的时间顺序
        if (i > 0) {
            const Segment& prev_seg = segments[i - 1];
            if (seg.start < prev_seg.end) {
                // 允许轻微重叠（小于0.1秒）
                if (prev_seg.end - seg.start > 0.1) {
                    return false;
                }
            }
        }
    }
    
    return true;
}

std::string format_srt_time(double seconds) {
    if (seconds < 0) {
        seconds = 0;
    }
    
    int hours = static_cast<int>(seconds / 3600);
    int minutes = static_cast<int>((seconds - hours * 3600) / 60);
    double remaining_seconds = seconds - hours * 3600 - minutes * 60;
    
    int secs = static_cast<int>(remaining_seconds);
    int milliseconds = static_cast<int>((remaining_seconds - secs) * 1000);
    
    std::ostringstream oss;
    oss << std::setfill('0') 
        << std::setw(2) << hours << ":"
        << std::setw(2) << minutes << ":"
        << std::setw(2) << secs << ","
        << std::setw(3) << milliseconds;
    
    return oss.str();
}

} // namespace v2s