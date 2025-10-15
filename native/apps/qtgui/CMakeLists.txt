cmake_minimum_required(VERSION 3.20)

set(CMAKE_AUTOMOC ON)
set(CMAKE_AUTOUIC OFF)
set(CMAKE_AUTORCC OFF)

find_package(Qt6 COMPONENTS Widgets REQUIRED)

add_executable(v2s_qt WIN32
    src/main.cpp
    src/MainWindow.cpp
    src/MainWindow.h
    src/ModelManagerDialog.cpp
    src/ModelManagerDialog.h
)

target_link_libraries(v2s_qt PRIVATE Qt6::Widgets v2s_core)

# 在 Windows 下为 WIN32 子系统链接 Qt 的入口库 (qtmain)，以支持使用标准 main() 作为入口
if(WIN32)
    if(TARGET Qt6::WinMain)
        target_link_libraries(v2s_qt PRIVATE Qt6::WinMain)
    else()
        # Fallback: 在某些 Qt 6 版本下，WinMain 入口库可能以不同名称提供
        find_library(QTMAIN_LIB NAMES qtmain Qt6EntryPoint Qt6EntryPointPrivate)
        if(QTMAIN_LIB)
            target_link_libraries(v2s_qt PRIVATE ${QTMAIN_LIB})
        endif()
    endif()
endif()

target_compile_features(v2s_qt PRIVATE cxx_std_17)

set_target_properties(v2s_qt PROPERTIES OUTPUT_NAME "v2s_qt")

# --- Windows 下构建后自动部署 Qt 运行时与第三方 DLL ---
if(WIN32 AND V2S_DEPLOY_ON_BUILD)
    # 解析 windeployqt 可执行路径（支持通过 -DV2S_WINDEPLOYQT_EXE 覆盖）
    if(NOT V2S_WINDEPLOYQT_EXE)
        if(TARGET Qt6::Core)
            get_target_property(_qtcore_loc Qt6::Core IMPORTED_LOCATION)
            if(_qtcore_loc)
                get_filename_component(_qtcore_libdir "${_qtcore_loc}" DIRECTORY)
                get_filename_component(V2S_QT_PREFIX "${_qtcore_libdir}" DIRECTORY)
                set(V2S_WINDEPLOYQT_EXE "${V2S_QT_PREFIX}/bin/windeployqt.exe")
            endif()
        endif()
    endif()

    # 运行 windeployqt 部署 Qt 运行时
    if(EXISTS "${V2S_WINDEPLOYQT_EXE}")
        set(_windeploy_mode "$<IF:$<CONFIG:Debug>,--debug,--release>")
        add_custom_command(TARGET v2s_qt POST_BUILD
            COMMAND "${V2S_WINDEPLOYQT_EXE}" --compiler-runtime ${_windeploy_mode} "$<TARGET_FILE:v2s_qt>"
            COMMENT "Run windeployqt to deploy Qt runtime"
        )
    else()
        message(STATUS "[deploy] windeployqt.exe not found; skip Qt runtime deployment. Set -DV2S_WINDEPLOYQT_EXE=...")
    endif()

    # 拷贝 FFmpeg DLL 到 GUI 可执行目录
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
        add_custom_command(TARGET v2s_qt POST_BUILD
            COMMAND ${CMAKE_COMMAND} -E copy_if_different "${_dll}" "$<TARGET_FILE_DIR:v2s_qt>"
            COMMENT "Copy FFmpeg runtime to GUI: ${_dll}"
        )
    endforeach()

    # 拷贝 MinGW 运行时 DLL 到 GUI 可执行目录
    get_filename_component(_mingw_bin_dir "${CMAKE_CXX_COMPILER}" DIRECTORY)
    foreach(_name IN ITEMS libstdc++-6.dll libgcc_s_seh-1.dll libwinpthread-1.dll libgomp-1.dll)
        set(_src "${_mingw_bin_dir}/${_name}")
        if(EXISTS "${_src}")
            add_custom_command(TARGET v2s_qt POST_BUILD
                COMMAND ${CMAKE_COMMAND} -E copy_if_different "${_src}" "$<TARGET_FILE_DIR:v2s_qt>"
                COMMENT "Copy MinGW runtime to GUI: ${_name}"
            )
        endif()
    endforeach()
endif()

# --- 构建后拷贝默认配置到 GUI 可执行目录的 config 子目录 ---
if(V2S_COPY_DEFAULT_CONFIG_ON_BUILD AND EXISTS "${V2S_DEFAULT_CONFIG_PATH}")
    add_custom_command(TARGET v2s_qt POST_BUILD
        COMMAND ${CMAKE_COMMAND} -E make_directory "$<TARGET_FILE_DIR:v2s_qt>/config"
        COMMAND ${CMAKE_COMMAND} -E copy_if_different "${V2S_DEFAULT_CONFIG_PATH}" "$<TARGET_FILE_DIR:v2s_qt>/config/default_config.json"
        COMMENT "Copy default_config.json to GUI config directory"
    )
endif()