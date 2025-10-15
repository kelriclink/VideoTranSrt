cmake_minimum_required(VERSION 3.20)
project(video2srt_native LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

# 为IDE/LSP生成编译数据库，解决代码提示与包含路径解析问题
set(CMAKE_EXPORT_COMPILE_COMMANDS ON)

# Disable OpenMP for GGML to avoid linking issues with MinGW
set(GGML_OPENMP OFF CACHE BOOL "Disable OpenMP for GGML" FORCE)

# 设置编译器标志
if(MINGW)
    # 仅静态链接 libgcc，避免与第三方静态库（如 whisper.cpp/ggml）在 MinGW 下产生不兼容的 libstdc++ 依赖
    # 静态链接 libstdc++ 可能导致某些符号（如 std::codecvt）解析失败，改为动态链接以提升兼容性。
    set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -static-libgcc")
endif()

# 子模块
add_subdirectory(libs/core)
add_subdirectory(apps/cli)
add_subdirectory(apps/qtgui)

enable_testing()
# add_subdirectory(tests) # 后续添加