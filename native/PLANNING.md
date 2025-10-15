# Video2SRT 原生（C/C++ + CMake）子项目规划书

本文档面向在不改动原 Python 项目的前提下，新增一个使用 CMake 的 C/C++ 子项目（位于 `native/` 目录）。目标是在保持现有功能稳定的同时，为性能敏感环节提供原生实现与后续可选的 Python 扩展绑定。

## 1. 设计目标与不改动原则
- 原项目不动：不修改 `video2srt/`、`setup.py`、`pyproject.toml`、现有 CI/workflow。
- 新增一个独立的原生子项目：`native/`，使用 CMake 构建，产物（exe / dll / pyd）放在 `native/build/` 或单独 `native/dist/`。
- 渐进式迭代：先搭建最小可构建骨架，再逐步接入音频提取与转录后端，最后考虑 Python 绑定与与 GUI/CLI 的联动。

## 2. 当前项目结构与处理流程（简述）
- 核心流程（`video2srt/core.py`）：
  1) 提取音频（`audio_extractor.py`）
  2) Whisper 转录（`transcriber.py` + `model_loaders.py` + `plugins/*`）
  3) 可选翻译（`translator.py` / `translator_manager.py`）
  4) 格式化输出（`formatter.py`），支持 `srt/vtt/ass`（`output_formats.py`）。
- 插件与模型加载：项目有 `plugins/` 与多种加载器（标准/优化/OpenVINO/Intel GPU/INT8、distil-whisper等）。
- CLI/GUI：`video2srt/cli.py` 提供命令行入口，`video2srt/gui` 提供图形界面。

原生子项目将以“并行实现”的方式引入：优先在 C++ 中实现音频提取 + 基础 SRT 生成，后续再对接 Whisper 推理（选择 whisper.cpp / ONNX Runtime / OpenVINO 的 C++ API）。

## 3. 分阶段目标
- 阶段 A（骨架）：
  - 完成 `native/` 目录与 CMake 骨架（已建立）。
  - `libs/core` 提供基础 API（版本号、占位函数）。
  - `apps/cli` 提供占位 CLI，可输出版本信息。
- 阶段 B（音频提取与预处理）：
  - 在 C++ 中使用 FFmpeg（libavformat/libavcodec/libswresample）将输入视频/音频解码为统一采样率、单声道的 PCM/WAV（例如 16kHz mono s16le）。
  - 与 Python 的 `audio_extractor.py` 对齐输入/输出约定（输入多媒体路径，输出本地 WAV）。
- 阶段 C（转录后端集成）：择一先行，逐步完善
  - 方案 C1：whisper.cpp（C/C++ 原生实现，ggml 后端，支持量化与跨平台）
  - 方案 C2：ONNX Runtime（如将模型转换为 ONNX 并采用 CPU/GPU 推理）
  - 方案 C3：OpenVINO（与现有项目插件保持一致的 CPU/GPU/设备支持）
  - 第一步输出基本字幕段（start/end/text），对齐 `models.py` 的 Segment 结构。
- 阶段 D（SRT/VTT/ASS 格式化与I/O）：
  - 实现 SRT/VTT/ASS 写入器（C++），或直接复用现有 Python 的格式器，通过文件桥接。
- 阶段 E（可选：翻译器）：
  - 初期可沿用 Python 翻译器（通过文件/管道），后期视需求在 C++ 中集成 HTTP 客户端（libcurl）与各翻译服务。
- 阶段 F（Python 绑定，pybind11 可选）：
  - 将部分性能敏感函数以 `video2srt_native` 扩展模块暴露给 Python（.pyd），供现有 Python 代码选择性使用。
- 阶段 G（CI 与发布）：
  - 新增独立的 `windows-native.yml` 工作流（不改动现有 `windows-release.yml`），进行 CMake 构建、单元测试与产物归档。

## 4. 目录与构建
- 顶层 CMake：`native/CMakeLists.txt`（已创建）
- 核心库：`native/libs/core`（已创建）
- CLI 程序：`native/apps/cli`（已创建）
- vcpkg 清单：`native/vcpkg.json`（已创建，声明若干可选特性与依赖）
- 构建命令（Windows）：
  - `cmake -S native -B native/build -G "Ninja" -DCMAKE_BUILD_TYPE=Release`
  - `cmake --build native/build --target v2s_cli`
  - 后续可增加 `ctest` 与安装打包目标。

## 5. 依赖库与选择理由
- 音频/视频解码（核心）：
  - FFmpeg（libavformat, libavcodec, libavutil, libswresample）用于多格式解码与重采样。[参考：vcpkg ffmpeg 端口 https://vcpkg.link/ports/ffmpeg]
- 语音识别后端（可选其一或多种并存）：
  - whisper.cpp：C/C++ 实现，依赖 ggml，支持量化，跨平台易分发。[参考：vcpkg whisper-cpp 端口 https://vcpkg.link/ports/whisper-cpp，项目主页 https://github.com/ggml-org/whisper.cpp]
  - ONNX Runtime：ONNX 推理引擎（CPU/GPU），配合模型转换与优化。[参考：vcpkg onnxruntime 端口示例 https://github.com/microsoft/vcpkg/blob/master/ports/onnxruntime-gpu/vcpkg.json]
  - OpenVINO：Intel 的高性能推理工具链，项目已有 OpenVINO 相关插件，C++ 接口适合集成。[参考：vcpkg openvino 端口 https://vcpkg.link/ports/openvino]
- 格式化与工具：
  - nlohmann/json：配置与数据结构序列化（轻量、单头文件）。
  - spdlog：高性能日志库。
  - cxxopts：命令行参数解析，简洁易用。
- 网络下载（后续可选）：
  - libcurl：模型与资源下载（如后续需要原生下载器）。

说明：现有 Python 项目已覆盖模型下载与管理（HuggingFace/多源动态 URL 等），原生子项目初期可不承担下载任务，仅消费本地模型文件。

## 6. 接口与数据约定
- 输入：多媒体文件路径（mp4/mkv/mp3/wav/…），或已提取的 WAV 文件路径。
- 输出：
  - 中间产物：WAV（统一采样率/单声道）
  - 识别结果：字幕段列表（start_ms, end_ms, text, language）
  - 最终产物：SRT/VTT/ASS 文件（与 Python 项目一致的命名策略）
- 约定：
  - 时间线精度与格式化规则与 `formatter.py` 对齐（00:00:01,000 等）。
  - 语言检测与标签若由后端提供，则直接复用；否则按需要在 C++ 或 Python 侧实现。

## 7. 构建与依赖管理（Windows）
- 推荐使用 vcpkg（manifest 模式）：
  - 进入项目根目录，安装 vcpkg 并启用清单：
    - `git clone https://github.com/microsoft/vcpkg.git`
    - `.\\vcpkg\\bootstrap-vcpkg.bat`
    - CMake 生成时添加：`-DCMAKE_TOOLCHAIN_FILE="<vcpkg_root>\\scripts\\buildsystems\\vcpkg.cmake"`
  - 选择特性：
    - 纯 CLI：默认依赖 `nlohmann-json`、`spdlog`、`cxxopts`
    - 音频提取：`-DVIDEO2SRT_NATIVE_FEATURES=audio`
    - 推理后端：`-DVIDEO2SRT_NATIVE_FEATURES=whisper-cpp` 或 `onnxruntime` 或 `openvino`
- 生成器：Ninja 或 Visual Studio（均可）。

## 8. 里程碑与任务
- M0 骨架完成（当前）：目录、CMake、占位 CLI
- M1 音频提取（FFmpeg）：支持常见视频/音频输入，输出规范化 WAV
- M2 转录后端（先集成 whisper.cpp）：产出字幕段；评估准确率与性能
- M3 字幕格式化（SRT/VTT/ASS）：实现 C++ 写入器，与 Python 对齐
- M4 兼容管理：统一配置（JSON）、日志（spdlog）、错误处理
- M5 可选 Python 扩展（pybind11）：暴露高频函数供 Python 调用
- M6 CI 集成：新增 `windows-native.yml`，编译与测试产物

## 9. 风险与替代方案
- 模型格式兼容性：
  - whisper.cpp 使用 ggml 模型，与 Python 端的原始 PyTorch 模型不直接兼容；需单独下载或转换（已存在成熟转换与发布渠道）。
- 依赖体积与发布：
  - FFmpeg/ONNX/OpenVINO 均可能带来较大发布体积；可考虑按特性拆分、可选组件下载。
- GPU/硬件适配：
  - 不同后端与硬件支持差异大（CUDA/CPU/OpenVINO/GPU），需针对性测试与文档说明。
- 维护成本：
  - 原生与 Python 并存带来协同成本；建议明确边界与模块职责，优先原生实现性能瓶颈模块。

## 10. 参考与链接
- FFmpeg（vcpkg 端口）：https://vcpkg.link/ports/ffmpeg
- whisper.cpp（vcpkg 端口）：https://vcpkg.link/ports/whisper-cpp；项目主页：https://github.com/ggml-org/whisper.cpp
- ONNX Runtime（vcpkg 示例端口定义）：https://github.com/microsoft/vcpkg/blob/master/ports/onnxruntime-gpu/vcpkg.json
- OpenVINO（vcpkg 端口）：https://vcpkg.link/ports/openvino
- 社区讨论（Whisper 的 OpenVINO/ONNX 加速思路）：https://github.com/openai/whisper/discussions/208

---

后续行动建议：先完成 M1（FFmpeg 音频提取），我可以在 `libs/core` 下新增 `audio` 子模块与初始实现（不影响原项目），你确认后我继续推进。