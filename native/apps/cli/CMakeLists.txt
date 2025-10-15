add_executable(v2s_cli
    src/main.cpp
)

target_link_libraries(v2s_cli
    PRIVATE
        v2s_core
)

set_target_properties(v2s_cli PROPERTIES OUTPUT_NAME "v2s_cli")

# --- Windows 下构建后自动拷贝第三方 DLL（FFmpeg、MinGW 运行时）到 CLI 可执行目录 ---
if(WIN32 AND V2S_DEPLOY_ON_BUILD)
    # 拷贝 FFmpeg DLL 到 CLI 可执行目录
    set(_ffmpeg_bin "${V2S_THIRD_PARTY_DIR}/ffmpeg/bin")
    set(_ffmpeg_lib "${V2S_THIRD_PARTY_DIR}/ffmpeg/lib")
    set(_ffmpeg_dlls)
    if(EXISTS "${_ffmpeg_bin}")
        file(GLOB _ffmpeg_bin_dlls "${_ffmpeg_bin}/*.dll")
        list(APPEND _ffmpeg_dlls ${_ffmpeg_bin_dlls})
    endif()
    if(EXISTS "${_ffmpeg_lib}")
        file(GLOB _ffmpeg_lib_dlls "${_ffmpeg_lib}/*.dll")
        list(APPEND _ffmpeg_dlls ${_ffmpeg_lib_dlls})
    endif()
    foreach(_dll ${_ffmpeg_dlls})
        add_custom_command(TARGET v2s_cli POST_BUILD
            COMMAND ${CMAKE_COMMAND} -E copy_if_different "${_dll}" "$<TARGET_FILE_DIR:v2s_cli>"
            COMMENT "Copy FFmpeg runtime to CLI: ${_dll}"
        )
    endforeach()

    # 拷贝 MinGW 运行时 DLL 到 CLI 可执行目录
    get_filename_component(_mingw_bin_dir "${CMAKE_CXX_COMPILER}" DIRECTORY)
    foreach(_name IN ITEMS libstdc++-6.dll libgcc_s_seh-1.dll libwinpthread-1.dll libgomp-1.dll)
        set(_src "${_mingw_bin_dir}/${_name}")
        if(EXISTS "${_src}")
            add_custom_command(TARGET v2s_cli POST_BUILD
                COMMAND ${CMAKE_COMMAND} -E copy_if_different "${_src}" "$<TARGET_FILE_DIR:v2s_cli>"
                COMMENT "Copy MinGW runtime to CLI: ${_name}"
            )
        endif()
    endforeach()
endif()

# --- 构建后拷贝默认配置到 CLI 可执行目录的 config 子目录 ---
if(V2S_COPY_DEFAULT_CONFIG_ON_BUILD AND EXISTS "${V2S_DEFAULT_CONFIG_PATH}")
    add_custom_command(TARGET v2s_cli POST_BUILD
        COMMAND ${CMAKE_COMMAND} -E make_directory "$<TARGET_FILE_DIR:v2s_cli>/config"
        COMMAND ${CMAKE_COMMAND} -E copy_if_different "${V2S_DEFAULT_CONFIG_PATH}" "$<TARGET_FILE_DIR:v2s_cli>/config/default_config.json"
        COMMENT "Copy default_config.json to CLI config directory"
    )
endif()