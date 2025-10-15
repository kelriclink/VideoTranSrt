# 编译器与工具路径 Tips（Windows）

- MinGW 13.1.0（随 Qt 安装的工具链）
  - 根目录：C:\Qt\Tools\mingw1310_64\bin
  - C 编译器（gcc）：C:\Qt\Tools\mingw1310_64\bin\gcc.exe
  - C++ 编译器（g++）：C:\Qt\Tools\mingw1310_64\bin\g++.exe

- Qt 6.10.0（用于部署与 CMake 前缀）
  - CMAKE_PREFIX_PATH：C:\Qt\6.10.0\mingw_64
  - windeployqt.exe：C:\Qt\6.10.0\mingw_64\bin\windeployqt.exe

- 常见注意事项
  - Qt 6.10.0 的 mingw_64\bin 目录通常不包含 gcc/g++；编译器位于 Tools\mingw1310_64\bin。
  - 若 CMake 报“找不到编译器”，请确认以上路径是否正确，并将 C:\Qt\Tools\mingw1310_64\bin 加入 PATH。

- 可选工具（若使用 Ninja 生成器）
  - Ninja 可执行路径（示例）：D:\kelric_soft\videotransrt\.venv\Scripts\ninja.exe

- CMake 变量示例（按需填写）
  - CMAKE_C_COMPILER=C:\Qt\Tools\mingw1310_64\bin\gcc.exe
  - CMAKE_CXX_COMPILER=C:\Qt\Tools\mingw1310_64\bin\g++.exe
  - CMAKE_PREFIX_PATH=C:\Qt\6.10.0\mingw_64
  - V2S_WINDEPLOYQT_EXE=C:\Qt\6.10.0\mingw_64\bin\windeployqt.exe