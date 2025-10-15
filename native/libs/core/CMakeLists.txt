# 定义核心库
add_library(v2s_core STATIC
    src/core.cpp
    src/audio.cpp
    src/models.cpp
    src/formatter.cpp
    src/output_formats.cpp
    src/transcriber.cpp
    src/processor.cpp
    src/translator.cpp
    src/config_manager.cpp
    src/model_manager.cpp
)
target_include_directories(v2s_core
    PUBLIC
        ${CMAKE_CURRENT_SOURCE_DIR}/include
)

# 查找FFmpeg库
find_package(PkgConfig QUIET)
if(PKG_CONFIG_FOUND)
    pkg_check_modules(FFMPEG QUIET libavformat libavcodec libavutil libswresample)
endif()

# 在Windows上确保链接WinHTTP（用于Google翻译实现）
if(WIN32)
    target_sources(v2s_core PRIVATE 
        src/google_translator.cpp
        src/openai_translator.cpp
    )
    # 避免重复链接，CMake会自动去重
    target_link_libraries(v2s_core PRIVATE winhttp)
endif()

# 检查FFmpeg是否可用
if(FFMPEG_FOUND)
    message(STATUS "Found FFmpeg libraries via pkg-config")
    target_compile_definitions(v2s_core PRIVATE V2S_HAVE_FFMPEG=1)
    target_link_libraries(v2s_core PRIVATE ${FFMPEG_LIBRARIES})
    target_include_directories(v2s_core PRIVATE ${FFMPEG_INCLUDE_DIRS})
    target_compile_options(v2s_core PRIVATE ${FFMPEG_CFLAGS_OTHER})
else()
    # 尝试直接链接FFmpeg库（Windows环境）
    # 设置FFmpeg路径
    set(FFMPEG_ROOT "${CMAKE_CURRENT_SOURCE_DIR}/../../third_party/ffmpeg")
    
    # 查找头文件
    find_path(FFMPEG_INCLUDE_DIR 
        NAMES libavformat/avformat.h
        PATHS ${FFMPEG_ROOT}/include
        NO_DEFAULT_PATH
    )
    
    # 查找库文件（MinGW格式）
    find_library(AVFORMAT_LIB 
        NAMES libavformat.dll.a avformat
        PATHS ${FFMPEG_ROOT}/lib
        NO_DEFAULT_PATH
    )
    find_library(AVCODEC_LIB 
        NAMES libavcodec.dll.a avcodec
        PATHS ${FFMPEG_ROOT}/lib
        NO_DEFAULT_PATH
    )
    find_library(AVUTIL_LIB 
        NAMES libavutil.dll.a avutil
        PATHS ${FFMPEG_ROOT}/lib
        NO_DEFAULT_PATH
    )
    find_library(SWRESAMPLE_LIB 
        NAMES libswresample.dll.a swresample
        PATHS ${FFMPEG_ROOT}/lib
        NO_DEFAULT_PATH
    )
    
    if(FFMPEG_INCLUDE_DIR AND AVFORMAT_LIB AND AVCODEC_LIB AND AVUTIL_LIB AND SWRESAMPLE_LIB)
        message(STATUS "Found FFmpeg libraries at ${FFMPEG_ROOT}")
        target_compile_definitions(v2s_core PRIVATE V2S_HAVE_FFMPEG=1)
        target_include_directories(v2s_core PRIVATE ${FFMPEG_INCLUDE_DIR})
        target_link_libraries(v2s_core PRIVATE 
            ${AVFORMAT_LIB} 
            ${AVCODEC_LIB} 
            ${AVUTIL_LIB} 
            ${SWRESAMPLE_LIB}
        )
        # 添加Windows系统库依赖
        if(WIN32)
            target_link_libraries(v2s_core PRIVATE ws2_32 secur32 bcrypt winhttp)
        endif()
    else()
        message(WARNING "FFmpeg not found at ${FFMPEG_ROOT}, building without FFmpeg support")
        target_compile_definitions(v2s_core PRIVATE V2S_HAVE_FFMPEG=0)
    endif()
endif()

option(V2S_ENABLE_WHISPER "Enable Whisper.cpp support" ON)

# 查找Whisper.cpp库
set(WHISPER_ROOT "${CMAKE_CURRENT_SOURCE_DIR}/../../third_party/whisper.cpp")

# 查找Whisper头文件
find_path(WHISPER_INCLUDE_DIR 
    NAMES whisper.h
    PATHS ${WHISPER_ROOT}/include
    NO_DEFAULT_PATH
)

# 查找GGML头文件
find_path(GGML_INCLUDE_DIR 
    NAMES ggml.h
    PATHS ${WHISPER_ROOT}/ggml/include
    NO_DEFAULT_PATH
)

# 支持多种第三方构建输出目录（Ninja/MinGW）
set(WHISPER_BUILD_DIRS
    # 优先使用 MinGW 构建产物，避免与其他工具链产物混用导致链接符号不匹配
    ${WHISPER_ROOT}/build-mingw/src
    ${WHISPER_ROOT}/build/src
)

# 重新计算库路径，避免使用缓存中的旧路径
unset(WHISPER_LIB CACHE)
unset(GGML_LIB CACHE)
unset(GGML_BASE_LIB CACHE)
unset(GGML_CPU_LIB CACHE)

# 查找Whisper库文件
find_library(WHISPER_LIB 
    NAMES libwhisper.a whisper
    PATHS ${WHISPER_BUILD_DIRS}
    NO_DEFAULT_PATH
)

# 查找GGML库文件
find_library(GGML_LIB 
    NAMES ggml.a ggml
    PATHS ${WHISPER_ROOT}/build-mingw/ggml/src ${WHISPER_ROOT}/build/ggml/src
    NO_DEFAULT_PATH
)

find_library(GGML_BASE_LIB 
    NAMES ggml-base.a ggml-base
    PATHS ${WHISPER_ROOT}/build-mingw/ggml/src ${WHISPER_ROOT}/build/ggml/src
    NO_DEFAULT_PATH
)

find_library(GGML_CPU_LIB 
    NAMES ggml-cpu.a ggml-cpu
    PATHS ${WHISPER_ROOT}/build-mingw/ggml/src ${WHISPER_ROOT}/build/ggml/src
    NO_DEFAULT_PATH
)

if(V2S_ENABLE_WHISPER AND WHISPER_INCLUDE_DIR AND GGML_INCLUDE_DIR AND WHISPER_LIB AND GGML_LIB AND GGML_BASE_LIB AND GGML_CPU_LIB)
    message(STATUS "Found Whisper.cpp libraries at ${WHISPER_ROOT}")
    target_compile_definitions(v2s_core PRIVATE V2S_HAVE_WHISPER=1)
    target_include_directories(v2s_core PRIVATE 
        ${WHISPER_INCLUDE_DIR}
        ${GGML_INCLUDE_DIR}
    )
    target_link_libraries(v2s_core PRIVATE 
        ${WHISPER_LIB}
        ${GGML_LIB}
        ${GGML_BASE_LIB}
        ${GGML_CPU_LIB}
    )
    # 添加OpenMP支持（如果可用）
    find_package(OpenMP)
    if(OpenMP_CXX_FOUND)
        target_link_libraries(v2s_core PRIVATE OpenMP::OpenMP_CXX)
    else()
        # 如果找不到OpenMP，尝试手动链接gomp库（MinGW环境）
        if(MINGW)
            target_link_libraries(v2s_core PRIVATE gomp)
            # 显式链接 C++ 标准库，避免在某些 MinGW 组合下出现 std::codecvt 等符号解析失败
            target_link_libraries(v2s_core PRIVATE stdc++)
        endif()
    endif()
else()
    if(V2S_ENABLE_WHISPER)
        message(WARNING "Whisper.cpp not found at ${WHISPER_ROOT}, building without Whisper support")
    else()
        message(STATUS "Whisper.cpp support disabled by option V2S_ENABLE_WHISPER=OFF")
    endif()
    target_compile_definitions(v2s_core PRIVATE V2S_HAVE_WHISPER=0)
endif()