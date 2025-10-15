#pragma once

#include <string>

namespace v2s {

// 简单版本信息接口，占位以验证构建
std::string version();

// 是否编译了 FFmpeg 支持（用于 CLI 显示与功能开关）
bool has_ffmpeg();

}