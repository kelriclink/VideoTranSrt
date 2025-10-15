#pragma once

#include <string>

namespace v2s {

// 将输入多媒体（视频/音频）解码为统一 WAV（如 16 kHz mono s16le）
// 返回 true 表示成功，false 表示失败（可在日志中输出错误原因）。
bool extract_audio_to_wav(const std::string& input_path,
                          const std::string& output_wav_path,
                          int sample_rate = 16000);

}