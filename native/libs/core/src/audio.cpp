#include "video2srt_native/audio.hpp"
#include <cstdio>
#include <vector>
#include <stdexcept>
#include <iostream>
#include <filesystem>

#if V2S_HAVE_FFMPEG
extern "C" {
#include <libavformat/avformat.h>
#include <libavcodec/avcodec.h>
#include <libavutil/avutil.h>
#include <libavutil/channel_layout.h>
#include <libavutil/samplefmt.h>
#include <libswresample/swresample.h>
}
#endif

namespace v2s {

// 简易 WAV 头写入与更新工具
struct WavHeader {
    uint32_t sample_rate;
    uint16_t num_channels;
    uint16_t bits_per_sample;
    uint32_t data_size; // PCM 数据字节数
};

static void write_wav_header(FILE* f, const WavHeader& h) {
    // RIFF header
    fwrite("RIFF", 1, 4, f);
    uint32_t chunk_size = 36 + h.data_size;
    fwrite(&chunk_size, 4, 1, f);
    fwrite("WAVE", 1, 4, f);
    // fmt chunk
    fwrite("fmt ", 1, 4, f);
    uint32_t fmt_size = 16; // PCM
    fwrite(&fmt_size, 4, 1, f);
    uint16_t audio_format = 1; // PCM
    fwrite(&audio_format, 2, 1, f);
    fwrite(&h.num_channels, 2, 1, f);
    fwrite(&h.sample_rate, 4, 1, f);
    uint32_t byte_rate = h.sample_rate * h.num_channels * (h.bits_per_sample / 8);
    fwrite(&byte_rate, 4, 1, f);
    uint16_t block_align = h.num_channels * (h.bits_per_sample / 8);
    fwrite(&block_align, 2, 1, f);
    fwrite(&h.bits_per_sample, 2, 1, f);
    // data chunk
    fwrite("data", 1, 4, f);
    fwrite(&h.data_size, 4, 1, f);
}

bool extract_audio_to_wav(const std::string& input_path,
                          const std::string& output_wav_path,
                          int sample_rate) {
#if !V2S_HAVE_FFMPEG
    (void)input_path; (void)output_wav_path; (void)sample_rate;
    std::cerr << "错误: FFmpeg 支持未编译，无法进行音频提取" << std::endl;
    std::cerr << "请通过 vcpkg 安装 FFmpeg 并重新编译项目" << std::endl;
    return false;
#else
    // 检查输入文件是否存在
    if (!std::filesystem::exists(input_path)) {
        std::cerr << "错误: 输入文件不存在: " << input_path << std::endl;
        return false;
    }
    
    // 确保输出目录存在
    std::filesystem::path out_path(output_wav_path);
    if (out_path.has_parent_path()) {
        std::filesystem::create_directories(out_path.parent_path());
    }
    
    std::cout << "开始提取音频: " << input_path << " -> " << output_wav_path << std::endl;
    std::cout << "目标采样率: " << sample_rate << "Hz, 单声道, 16-bit PCM" << std::endl;
    AVFormatContext* fmt_ctx = nullptr;
    int ret = 0;

    if ((ret = avformat_open_input(&fmt_ctx, input_path.c_str(), nullptr, nullptr)) < 0) {
        return false;
    }
    if ((ret = avformat_find_stream_info(fmt_ctx, nullptr)) < 0) {
        avformat_close_input(&fmt_ctx);
        return false;
    }

    int audio_stream_index = av_find_best_stream(fmt_ctx, AVMEDIA_TYPE_AUDIO, -1, -1, nullptr, 0);
    if (audio_stream_index < 0) {
        avformat_close_input(&fmt_ctx);
        return false;
    }

    AVStream* audio_stream = fmt_ctx->streams[audio_stream_index];
    const AVCodec* dec = avcodec_find_decoder(audio_stream->codecpar->codec_id);
    if (!dec) {
        avformat_close_input(&fmt_ctx);
        return false;
    }

    AVCodecContext* dec_ctx = avcodec_alloc_context3(dec);
    if (!dec_ctx) {
        avformat_close_input(&fmt_ctx);
        return false;
    }
    if ((ret = avcodec_parameters_to_context(dec_ctx, audio_stream->codecpar)) < 0) {
        avcodec_free_context(&dec_ctx);
        avformat_close_input(&fmt_ctx);
        return false;
    }
    if ((ret = avcodec_open2(dec_ctx, dec, nullptr)) < 0) {
        avcodec_free_context(&dec_ctx);
        avformat_close_input(&fmt_ctx);
        return false;
    }

    // 目标参数：单声道、s16、指定采样率
    AVChannelLayout out_ch_layout;
    av_channel_layout_default(&out_ch_layout, 1);
    AVSampleFormat out_sample_fmt = AV_SAMPLE_FMT_S16;
    int out_sample_rate = sample_rate;

    SwrContext* swr = swr_alloc();
    if (!swr) {
        avcodec_free_context(&dec_ctx);
        avformat_close_input(&fmt_ctx);
        return false;
    }

    // 设置输入/输出参数 - 兼容新旧FFmpeg API
    int ret_swr = swr_alloc_set_opts2(&swr,
                        &out_ch_layout, out_sample_fmt, out_sample_rate,
                        &dec_ctx->ch_layout, dec_ctx->sample_fmt, dec_ctx->sample_rate,
                        0, nullptr);
    if (ret_swr < 0) {
        std::cerr << "错误: 无法配置重采样器" << std::endl;
        swr_free(&swr);
        avcodec_free_context(&dec_ctx);
        avformat_close_input(&fmt_ctx);
        return false;
    }
    if ((ret = swr_init(swr)) < 0) {
        swr_free(&swr);
        avcodec_free_context(&dec_ctx);
        avformat_close_input(&fmt_ctx);
        return false;
    }

    FILE* out = std::fopen(output_wav_path.c_str(), "wb");
    if (!out) {
        swr_free(&swr);
        avcodec_free_context(&dec_ctx);
        avformat_close_input(&fmt_ctx);
        return false;
    }

    // 占位写入 WAV 头，稍后补齐 data_size
    WavHeader hdr{ (uint32_t)out_sample_rate, (uint16_t)1, (uint16_t)16, 0 };
    write_wav_header(out, hdr);

    AVPacket* pkt = av_packet_alloc();
    AVFrame* frame = av_frame_alloc();
    std::vector<uint8_t> out_buf;
    int64_t total_samples = 0;
    int processed_packets = 0;
    
    std::cout << "开始解码和重采样..." << std::endl;

    while ((ret = av_read_frame(fmt_ctx, pkt)) >= 0) {
        if (pkt->stream_index != audio_stream_index) {
            av_packet_unref(pkt);
            continue;
        }
        if ((ret = avcodec_send_packet(dec_ctx, pkt)) < 0) {
            av_packet_unref(pkt);
            break;
        }
        av_packet_unref(pkt);

        while ((ret = avcodec_receive_frame(dec_ctx, frame)) >= 0) {
            // 计算输出样本数
            int out_nb_samples = av_rescale_rnd(swr_get_delay(swr, dec_ctx->sample_rate) + frame->nb_samples,
                                                out_sample_rate, dec_ctx->sample_rate, AV_ROUND_UP);

            int out_channels = out_ch_layout.nb_channels;
            int out_bytes_per_sample = av_get_bytes_per_sample(out_sample_fmt);
            int out_buf_size = out_nb_samples * out_channels * out_bytes_per_sample;
            out_buf.resize(out_buf_size);
            uint8_t* out_data[1] = { out_buf.data() };

            int converted = swr_convert(swr, out_data, out_nb_samples,
                                        (const uint8_t**)frame->extended_data, frame->nb_samples);
            if (converted < 0) {
                break;
            }

            int bytes_written = converted * out_channels * out_bytes_per_sample;
            if (bytes_written > 0) {
                fwrite(out_buf.data(), 1, bytes_written, out);
                total_samples += converted;
            }
            av_frame_unref(frame);
            processed_packets++;
            
            // 每处理1000个包显示一次进度
            if (processed_packets % 1000 == 0) {
                std::cout << "已处理 " << processed_packets << " 个音频包..." << std::endl;
            }
        }
    }

    // 刷新解码器
    avcodec_send_packet(dec_ctx, nullptr);
    while (avcodec_receive_frame(dec_ctx, frame) >= 0) {
        int out_nb_samples = av_rescale_rnd(swr_get_delay(swr, dec_ctx->sample_rate) + frame->nb_samples,
                                            out_sample_rate, dec_ctx->sample_rate, AV_ROUND_UP);
        int out_channels = out_ch_layout.nb_channels;
        int out_bytes_per_sample = av_get_bytes_per_sample(out_sample_fmt);
        int out_buf_size = out_nb_samples * out_channels * out_bytes_per_sample;
        out_buf.resize(out_buf_size);
        uint8_t* out_data[1] = { out_buf.data() };
        int converted = swr_convert(swr, out_data, out_nb_samples,
                                    (const uint8_t**)frame->extended_data, frame->nb_samples);
        if (converted > 0) {
            int bytes_written = converted * out_channels * out_bytes_per_sample;
            fwrite(out_buf.data(), 1, bytes_written, out);
            total_samples += converted;
        }
        av_frame_unref(frame);
    }

    // 更新 WAV 头部的 data_size 与 RIFF chunk size
    long file_pos = std::ftell(out);
    uint32_t data_size = (uint32_t)(total_samples * hdr.num_channels * (hdr.bits_per_sample / 8));
    // RIFF chunk size at offset 4
    std::fseek(out, 4, SEEK_SET);
    uint32_t riff_size = 36 + data_size;
    std::fwrite(&riff_size, 4, 1, out);
    // data chunk size at offset 40
    std::fseek(out, 40, SEEK_SET);
    std::fwrite(&data_size, 4, 1, out);
    std::fseek(out, file_pos, SEEK_SET);

    std::fclose(out);
    av_frame_free(&frame);
    av_packet_free(&pkt);
    swr_free(&swr);
    avcodec_free_context(&dec_ctx);
    avformat_close_input(&fmt_ctx);
    
    double duration_sec = (double)total_samples / sample_rate;
    std::cout << "音频提取完成!" << std::endl;
    std::cout << "输出文件: " << output_wav_path << std::endl;
    std::cout << "总样本数: " << total_samples << " (" << duration_sec << " 秒)" << std::endl;
    std::cout << "文件大小: " << (total_samples * hdr.num_channels * (hdr.bits_per_sample / 8) + 44) << " 字节" << std::endl;
    
    return true;
#endif
}

}