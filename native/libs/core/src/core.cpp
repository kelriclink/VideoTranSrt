#include "video2srt_native/core.hpp"

namespace v2s {

std::string version() {
    return "0.1.0";
}

bool has_ffmpeg() {
#if V2S_HAVE_FFMPEG
    return true;
#else
    return false;
#endif
}

}