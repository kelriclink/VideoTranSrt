cmake_minimum_required(VERSION 3.20)
project(video2srt_native LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

# 为IDE/LSP生成编译数据库，解决代码提示与包含路径解析问题
set(CMAKE_EXPORT_COMPILE_COMMANDS ON)

# Disable OpenMP for GGML to avoid linking issues with MinGW
set(GGML_OPENMP OFF CACHE BOOL "Disable OpenMP for GGML" FORCE)

# 通用依赖管理选项与路径（可由配置脚本或命令行覆盖）
option(V2S_USE_LOCAL_DEPS "优先使用 native/third_party 下的本地依赖" ON)
set(V2S_THIRD_PARTY_DIR "${CMAKE_CURRENT_SOURCE_DIR}/third_party" CACHE PATH "第三方依赖根目录")


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

# 部署选项：在 Windows 下构建后自动部署依赖
option(V2S_DEPLOY_ON_BUILD "Windows 平台在构建后自动部署 Qt 运行时与第三方 DLL" ON)

# 在构建后自动拷贝默认配置文件到可执行目录的 config 子目录
option(V2S_COPY_DEFAULT_CONFIG_ON_BUILD "构建后拷贝默认配置到可执行目录的 config 子目录" ON)
set(V2S_DEFAULT_CONFIG_PATH "${CMAKE_SOURCE_DIR}/../config/default_config.json" CACHE FILEPATH "默认配置文件路径")

enable_testing()
# add_subdirectory(tests) # 后续添加
