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