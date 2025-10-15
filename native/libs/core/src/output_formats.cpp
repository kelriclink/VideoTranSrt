#include "video2srt_native/output_formats.hpp"
#include "video2srt_native/models.hpp"
#include <sstream>
#include <iomanip>
#include <fstream>
#include <algorithm>
#include <cctype>

namespace v2s {

static std::vector<Segment> fix_segments_for_vtt(const std::vector<Segment>& segments,
                                                 double min_duration) {
    std::vector<Segment> fixed;
    fixed.reserve(segments.size());

    for (const auto& seg : segments) {
        std::string text = seg.text;
        // 简单trim
        text.erase(text.begin(), std::find_if(text.begin(), text.end(), [](unsigned char ch){ return !std::isspace(ch); }));
        text.erase(std::find_if(text.rbegin(), text.rend(), [](unsigned char ch){ return !std::isspace(ch); }).base(), text.end());
        if (text.empty()) continue;

        Segment s = seg;
        s.text = text;
        if (s.start < 0) s.start = 0.0;
        if (s.end <= s.start) s.end = s.start + min_duration;
        if ((s.end - s.start) < min_duration) s.end = s.start + min_duration;
        fixed.push_back(std::move(s));
    }

    std::sort(fixed.begin(), fixed.end(), [](const Segment& a, const Segment& b){ return a.start < b.start; });
    // 解决重叠
    double last_end = 0.0;
    for (auto& s : fixed) {
        if (s.start < last_end) s.start = last_end;
        if (s.end <= s.start) s.end = s.start + min_duration;
        last_end = s.end;
    }

    return fixed;
}

std::string WebVTTFormatter::format_vtt_time(double seconds) {
    if (seconds < 0) seconds = 0.0;
    int hours = static_cast<int>(seconds / 3600);
    int minutes = static_cast<int>((seconds - hours * 3600) / 60);
    double rem = seconds - hours * 3600 - minutes * 60;
    int secs = static_cast<int>(rem);
    int milliseconds = static_cast<int>((rem - secs) * 1000);

    std::ostringstream oss;
    oss << std::setfill('0')
        << std::setw(2) << hours << ":"
        << std::setw(2) << minutes << ":"
        << std::setw(2) << secs << "."
        << std::setw(3) << milliseconds;
    return oss.str();
}

std::string WebVTTFormatter::format_segments(const std::vector<Segment>& segments,
                                             double min_duration) {
    auto fixed = fix_segments_for_vtt(segments, min_duration);

    std::ostringstream vtt;
    vtt << "WEBVTT\n\n";
    for (size_t i = 0; i < fixed.size(); ++i) {
        const auto& s = fixed[i];
        vtt << format_vtt_time(s.start) << " --> " << format_vtt_time(s.end) << "\n";
        vtt << s.text << "\n\n";
    }
    return vtt.str();
}

bool WebVTTFormatter::save_vtt(const std::string& content,
                               const std::filesystem::path& output_path) {
    try {
        std::filesystem::create_directories(output_path.parent_path());
        std::ofstream file(output_path, std::ios::out | std::ios::trunc);
        if (!file.is_open()) return false;
        file << content;
        file.close();
        return true;
    } catch (...) {
        return false;
    }
}

std::string WebVTTFormatter::create_bilingual_vtt(const std::vector<Segment>& original_segments,
                                                   const std::vector<Segment>& translated_segments) {
    if (original_segments.size() != translated_segments.size()) {
        return format_segments(original_segments);
    }
    std::vector<Segment> merged;
    merged.reserve(original_segments.size());
    for (size_t i = 0; i < original_segments.size(); ++i) {
        Segment s = original_segments[i];
        s.text = original_segments[i].text + "\n" + translated_segments[i].text;
        merged.push_back(std::move(s));
    }
    return format_segments(merged);
}

// -------------------- ASS Formatter --------------------

static std::vector<Segment> fix_segments_for_ass(const std::vector<Segment>& segments,
                                                 double min_duration) {
    std::vector<Segment> fixed;
    fixed.reserve(segments.size());

    for (const auto& seg : segments) {
        std::string text = seg.text;
        // 简单trim
        text.erase(text.begin(), std::find_if(text.begin(), text.end(), [](unsigned char ch){ return !std::isspace(ch); }));
        text.erase(std::find_if(text.rbegin(), text.rend(), [](unsigned char ch){ return !std::isspace(ch); }).base(), text.end());
        if (text.empty()) continue;

        Segment s = seg;
        s.text = text;
        if (s.start < 0) s.start = 0.0;
        if (s.end <= s.start) s.end = s.start + min_duration;
        if ((s.end - s.start) < min_duration) s.end = s.start + min_duration;
        fixed.push_back(std::move(s));
    }

    std::sort(fixed.begin(), fixed.end(), [](const Segment& a, const Segment& b){ return a.start < b.start; });
    // 解决重叠
    double last_end = 0.0;
    for (auto& s : fixed) {
        if (s.start < last_end) s.start = last_end;
        if (s.end <= s.start) s.end = s.start + min_duration;
        last_end = s.end;
    }

    return fixed;
}

static std::string ass_escape_text(const std::string& text) {
    // 将换行替换为 \N，避免特殊字符冲突
    std::string out;
    out.reserve(text.size() + 8);
    for (char c : text) {
        if (c == '\n' || c == '\r') {
            out += "\\N";
        } else {
            out += c;
        }
    }
    return out;
}

std::string ASSFormatter::format_ass_time(double seconds) {
    if (seconds < 0) seconds = 0.0;
    int hours = static_cast<int>(seconds / 3600);
    int minutes = static_cast<int>((seconds - hours * 3600) / 60);
    double rem = seconds - hours * 3600 - minutes * 60;
    int secs = static_cast<int>(rem);
    int centis = static_cast<int>((rem - secs) * 100); // 百分之一秒

    std::ostringstream oss;
    oss << std::setfill('0')
        << hours << ":"
        << std::setw(2) << minutes << ":"
        << std::setw(2) << secs << "."
        << std::setw(2) << centis;
    return oss.str();
}

std::string ASSFormatter::format_segments(const std::vector<Segment>& segments,
                                          const ASSStyleConfig& style,
                                          double min_duration) {
    auto fixed = fix_segments_for_ass(segments, min_duration);

    // Header & Styles
    std::ostringstream ass;
    ass << "[Script Info]\n";
    ass << "ScriptType: v4.00+\n";
    ass << "WrapStyle: 0\n";
    ass << "ScaledBorderAndShadow: yes\n\n";

    ass << "[V4+ Styles]\n";
    ass << "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, "
           "Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, "
           "Alignment, MarginL, MarginR, MarginV, Encoding\n";
    // 采用简单的默认颜色组合，PrimaryColour使用配置，其余给定固定值
    ass << "Style: " << style.style_name << "," << style.font_name << "," << style.font_size << ","
        << style.primary_color << ",&H000000FF,&H00000000,&H3F000000," // Secondary/Outline/Back
        << 0 << "," << 0 << "," << 0 << "," << 0 << "," // Bold/Italic/Underline/StrikeOut
        << 100 << "," << 100 << "," << 0 << "," << 0 << "," // ScaleX/ScaleY/Spacing/Angle
        << 1 << "," << style.outline << "," << style.shadow << "," << style.alignment << "," // BorderStyle/Outline/Shadow/Alignment
        << 10 << "," << 10 << "," << 10 << "," << 1 << "\n\n"; // Margins/Encoding

    ass << "[Events]\n";
    ass << "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n";

    for (const auto& s : fixed) {
        ass << "Dialogue: 0,"
            << format_ass_time(s.start) << ","
            << format_ass_time(s.end) << ","
            << style.style_name << ",,0,0,0,,"
            << ass_escape_text(s.text) << "\n";
    }

    return ass.str();
}

bool ASSFormatter::save_ass(const std::string& content,
                            const std::filesystem::path& output_path) {
    try {
        std::filesystem::create_directories(output_path.parent_path());
        std::ofstream file(output_path, std::ios::out | std::ios::trunc);
        if (!file.is_open()) return false;
        file << content;
        file.close();
        return true;
    } catch (...) {
        return false;
    }
}

std::string ASSFormatter::create_bilingual_ass(const std::vector<Segment>& original_segments,
                                               const std::vector<Segment>& translated_segments,
                                               const ASSStyleConfig& style,
                                               double min_duration) {
    if (original_segments.size() != translated_segments.size()) {
        return format_segments(original_segments, style, min_duration);
    }
    std::vector<Segment> merged;
    merged.reserve(original_segments.size());
    for (size_t i = 0; i < original_segments.size(); ++i) {
        Segment s = original_segments[i];
        s.text = original_segments[i].text + "\n" + translated_segments[i].text;
        merged.push_back(std::move(s));
    }
    return format_segments(merged, style, min_duration);
}

} // namespace v2s