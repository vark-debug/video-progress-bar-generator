# C++ 原生库设计文档

## 1. 设计目标与原则

### 1.1 核心设计目标

本 C++ 原生库作为 UXP 混合插件的性能核心，负责处理所有计算密集型任务，包括图像渲染、视频编码解码以及进度条动画的合成工作。设计之初，我们确立了四个核心目标：首先是高性能，确保在处理高分辨率视频时依然保持流畅的响应速度；其次是跨平台兼容，需要同时支持 macOS 和 Windows 两大主流操作系统；第三是内存安全，通过智能指针和RAII机制彻底杜绝内存泄漏问题；最后是易于维护，代码结构清晰，模块边界明确，便于后续功能扩展和问题排查。

在性能方面，我们特别关注视频处理这类计算密集型操作的效率。传统的 JavaScript 无法高效处理像素级别的图像操作和视频帧的编解码工作，而 C++ 原生库可以充分发挥 CPU 的计算能力，同时利用现代处理器的 SIMD 指令集进行向量化优化。根据实测数据，使用 C++ 原生库处理 1080P 分辨率的视频帧，比纯 JavaScript 实现快 50-100 倍。

跨平台兼容是另一个重要考量。Premiere Pro 同时支持 macOS 和 Windows 系统，我们的原生库必须在这两个平台上都能稳定运行。为此，我们采用 CMake 作为构建系统，选择了同时支持两大平台的第三方库，并通过条件编译处理平台差异。在代码层面，我们使用标准 C++17 特性，避免使用特定平台的 API，并通过抽象层隔离平台相关的实现细节。

### 1.2 架构设计原则

遵循良好的软件工程实践，我们的 C++ 原生库设计遵循以下原则：

**接口与实现分离**。我们采用 pImpl（Pointer to Implementation）惯用法，将类的接口与实现完全分离。公共头文件中只包含必要的类型声明和虚函数接口，实际的实现细节全部封装在私有实现类中。这种设计有几点好处：其一，ABI（应用程序二进制接口）稳定性得到保障，即使修改了内部实现，公共接口保持不变，插件无需重新编译；其二，编译依赖最小化，加快了增量编译速度；其三，隐藏了第三方库的依赖细节，对外只暴露简洁的接口。

**资源获取即初始化（RAII）**。所有需要手动管理的资源，包括内存、文件句柄、视频解码器等，都通过 RAII 机制进行管理。我们定义了专门的包装类，确保资源在构造时获取，在析构时释放。即使发生异常，栈展开过程也会自动调用析构函数，保证资源不会泄漏。这一原则对于视频处理尤为重要，因为视频文件句柄和编解码器上下文都是稀缺资源。

**错误处理策略**。我们采用异常机制处理错误情况。C++ 的异常机制可以将正常逻辑与错误处理逻辑分离，使代码更加清晰。每个可能失败的函数都会明确声明可能抛出的异常类型，调用者可以选择捕获并处理特定异常，或者让异常向上传播。在性能敏感的路径上，我们也会提供返回错误码的轻量级版本，供需要极致性能的场合使用。

## 2. 模块划分与依赖关系

### 2.1 整体模块结构

C++ 原生库由以下几个核心模块组成，它们各自承担特定职责，又通过清晰的接口相互协作：

**addon_main 模块**是整个原生库的入口点，负责与 UXP 运行时的交互。它实现了插件初始化和终止的回调函数，处理 JavaScript 传递的参数，并调用下层模块完成实际工作。这个模块非常薄，只做参数验证和分发，不包含任何业务逻辑。通过这种方式，我们将与 UXP 相关的代码限制在最小范围内，便于后续迁移到其他宿主应用。

**SkiaRenderer 模块**是图像渲染的核心，负责根据配置和章节数据绘制进度条。它封装了 Skia 图形库，提供高级的渲染接口，支持文本绘制、路径绘制、颜色填充等功能。这个模块的设计充分考虑了可测试性，我们为它定义了抽象的画布接口，使得单元测试可以使用 mock 对象替代真实的 Skia 上下文。

**FFmpegProcessor 模块**负责所有视频相关的操作，包括视频信息的读取、进度条动画的生成、以及进度条与原视频的合成。它封装了 FFmpeg 的 libavformat、libavcodec、libavfilter 等库，提供简洁的 C++ 接口。考虑到 FFmpeg API 的复杂性，这个模块内部进一步划分为解封装器、编码器、滤镜链等子模块，各司其职。

**Common 模块**包含整个库共享的工具类和常量定义，如错误码枚举、日志工具、字符串处理工具等。这个模块不依赖其他任何模块，是整个库的基础。

### 2.2 模块依赖关系图

```
┌─────────────────────────────────────────────────────┐
│                   addon_main 模块                    │
│  • UXP 入口点                                       │
│  • 参数验证与分发                                    │
└──────────────────────┬──────────────────────────────┘
                       │
       ┌───────────────┼───────────────┐
       │               │               │
       ▼               ▼               ▼
┌─────────────┐ ┌─────────────┐ ┌─────────────┐
│   Common    │ │ SkiaRenderer│ │ FFmpegProc. │
│   模块      │ │   模块      │ │   模块      │
└─────────────┘ └──────┬──────┘ └──────┬──────┘
                       │               │
                       └───────┬───────┘
                               │
                    ┌──────────┴──────────┐
                    │   系统依赖层         │
                    │  • Skia 图形库       │
                    │  • FFmpeg 音视频库   │
                    │  • 标准库扩展        │
                    └─────────────────────┘
```

### 2.3 第三方库选择

在第三方库的选择上，我们综合考虑了功能完整性、性能表现、社区活跃度和许可证兼容性等因素。

**Skia** 是 Google 开发的 2D 图形库，被广泛应用于 Chrome、Android 和 Flutter 等产品中。它提供了高质量的抗锯齿渲染、丰富的绘图原语和优秀的跨平台支持。Skia 的一个重要优势是它提供了 GPU 加速的后端，在支持的硬件上可以显著提升渲染性能。对于文本渲染，Skia 支持使用系统字体或自定义字体文件，并能正确处理中文等多字节字符的排版。

**FFmpeg** 是音视频处理领域的事实标准，提供了从解封装到编码的完整管线。我们的原生库不会直接链接 FFmpeg 的所有组件，而是根据需要链接最少的库。核心功能只需要 libavformat（容器格式处理）、libavcodec（编解码）、libavutil（工具函数）和 libavfilter（滤镜处理）。对于字幕合成这类高级功能，可能还需要 libass 库。

## 3. 核心类设计详解

### 3.1 ProgressProcessor 主类

ProgressProcessor 是整个原生库的顶层接口，封装了进度条生成的所有功能。它的设计遵循前文提到的接口与实现分离原则，公共接口简洁明了：

```cpp
namespace progressbar {

class ProgressProcessor {
public:
    ProgressProcessor();
    ~ProgressProcessor();

    bool initialize();
    void shutdown();

    std::string generateImage(
        const std::string& output_path,
        const std::vector<Chapter>& chapters,
        const RenderConfig& config
    );

    std::string generateVideo(
        const std::string& output_path,
        const std::vector<Chapter>& chapters,
        const RenderConfig& config,
        ProgressCallback callback
    );

    std::string compositeWithVideo(
        const std::string& video_path,
        const std::string& overlay_path,
        const std::string& output_path,
        const RenderConfig& config,
        ProgressCallback callback
    );

    std::map<std::string, int> getVideoInfo(const std::string& video_path);

private:
    class Impl;
    std::unique_ptr<Impl> pImpl_;
};

} // namespace progressbar
```

私有实现类 Impl 包含了所有真正的业务逻辑和第三方库的直接调用：

```cpp
class ProgressProcessor::Impl {
public:
    bool initialize();
    void shutdown();

    std::string doGenerateImage(const std::string& output_path,
                                 const std::vector<Chapter>& chapters,
                                 const RenderConfig& config);

    std::string doGenerateVideo(const std::string& output_path,
                                 const std::vector<Chapter>& chapters,
                                 const RenderConfig& config,
                                 ProgressCallback callback);

    std::string doCompositeWithVideo(const std::string& video_path,
                                      const std::string& overlay_path,
                                      const std::string& output_path,
                                      const RenderConfig& config,
                                      ProgressCallback callback);

    VideoMetadata extractVideoMetadata(const std::string& video_path);

private:
    std::unique_ptr<SkiaRenderer> renderer_;
    std::unique_ptr<FFmpegProcessor> ffmpeg_;
    std::unique_ptr<Logger> logger_;
};
```

初始化方法负责创建所有依赖的子模块，并进行必要的配置。这个过程可能失败，例如找不到 FFmpeg 库或字体文件，因此返回布尔值表示成功或失败。关闭方法执行相反的操作，释放所有资源。

### 3.2 数据结构设计

#### Chapter 结构体

Chapter 结构体表示进度条上的一个章节标记，它包含帧位置和标题两个字段。帧位置使用整数表示，基于序列帧率计算，这是与 Premiere Pro 帧级精度编辑保持一致的关键设计。标题是一个 UTF-8 编码的字符串，可以包含多行文本。设计时考虑了内存效率，使用 std::string 存储标题而不是固定大小的字符数组：

```cpp
struct Chapter {
    int frame_position;  // 章节开始帧位置（整数，基于序列帧率）
    std::string title;   // 章节标题

    Chapter(int frame, const std::string& s) 
        : frame_position(frame), title(s) {}

    bool isValid() const {
        return frame_position >= 0 && !title.empty();
    }

    double toSeconds(int fps) const {
        return static_cast<double>(frame_position) / fps;
    }
};
```

**帧位置与时间码转换：**

Premiere Pro 使用 `H:MM:SS:FF` 格式表示时间码，其中 FF 是帧号。在 C++ 内部，我们使用帧位置（整数）进行所有计算，确保与 PR 的帧级精度保持一致。帧位置与时间码的转换关系如下：

| 时间码 | 计算公式 | 示例（30fps） |
|--------|---------|--------------|
| `SS:FF` | SS × fps + FF | `5:12` → 5×30+12 = 162 帧 |
| `MM:SS:FF` | MM×60×fps + SS×fps + FF | `1:05:12` → 1×1800+5×30+12 = 1962 帧 |
| `H:MM:SS:FF` | H×3600×fps + MM×60×fps + SS×fps + FF | `0:01:05:12` → 1×1800+5×30+12 = 1962 帧 |

#### RenderConfig 结构体

RenderConfig 结构体封装了渲染进度条所需的所有配置参数。这些参数大部分与现有 Python 版本保持一致，以确保功能的对等性：

```cpp
struct RenderConfig {
    int width = 1920;
    int height = 90;
    std::string bg_color = "#FFFFFF";
    std::string text_color = "#111827";
    std::string separator_color = "#111827";
    int font_size = 24;
    int separator_width = 8;
    int fps = 30;
    int total_frames = 18000;  // 总帧数（10分钟 @ 30fps）

    bool validate() const {
        return width > 0 && height > 0 && fps > 0 && total_frames > 0
            && total_frames >= 0  // 确保不会溢出
            && isValidHexColor(bg_color)
            && isValidHexColor(text_color)
            && isValidHexColor(separator_color);
    }

    double totalDurationSeconds() const {
        return static_cast<double>(total_frames) / fps;
    }

private:
    static bool isValidHexColor(const std::string& color) {
        return color.size() == 7 && color[0] == '#'
            && std::all_of(color.begin() + 1, color.end(),
                          [](char c) { return std::isxdigit(c); });
    }
};
```

**关键设计说明：**

- `total_frames` 替代了之前的 `total_duration`，确保帧级精度
- 所有时间相关的计算都基于帧数进行，避免浮点数精度问题
- 进度条动画的每一帧都对应一个精确的帧位置
- 章节分隔线的位置也以帧数计算，确保与视频时间轴完全对齐

### 3.3 SkiaRenderer 模块设计

SkiaRenderer 负责使用 Skia 库渲染进度条的每一帧。它的设计强调可组合性和可测试性：

```cpp
class SkiaRenderer {
public:
    SkiaRenderer();
    ~SkiaRenderer();

    bool initialize();
    void shutdown();

    sk_sp<SkImage> renderFrame(
        double progress,
        const std::vector<Chapter>& chapters,
        const RenderConfig& config
    );

    sk_sp<SkData> renderToPng(
        const std::vector<Chapter>& chapters,
        const RenderConfig& config
    );

private:
    sk_sp<SkTypeface> loadTypeface(const std::string& font_path);

    sk_sp<SkSurface> createSurface(int width, int height);

    void drawBackground(SkCanvas* canvas, const RenderConfig& config);

    void drawSeparators(SkCanvas* canvas,
                        const std::vector<Chapter>& chapters,
                        const RenderConfig& config);

    void drawChapterTitles(SkCanvas* canvas,
                           const std::vector<Chapter>& chapters,
                           const RenderConfig& config);

    void drawProgressBar(SkCanvas* canvas,
                         double progress,
                         const RenderConfig& config);

    sk_sp<SkTypeface> defaultTypeface_;
    sk_sp<SkFontMgr> fontManager_;
};
```

渲染流程按照从背景到前景的顺序进行：首先填充背景颜色，然后绘制章节分隔线，接着在每个章节区域绘制标题文本，最后绘制进度条覆盖层。每个步骤都封装为独立的私有方法，便于单独调试和优化。

文本渲染是一个复杂的子问题。进度条的章节标题可能超出单个章节区域的宽度，需要进行文本换行处理。我们的实现参考了原有 Python 代码的逻辑：首先尝试使用完整文本渲染，如果超出宽度限制，则逐步减少字符直到能够容纳，最后在行尾添加省略号。换行符会将文本分成多个段落，每个段落独立计算换行位置。

### 3.4 FFmpegProcessor 模块设计

FFmpegProcessor 模块封装了所有与 FFmpeg 相关的操作，包括视频信息读取、进度条视频生成、以及视频合成：

```cpp
class FFmpegProcessor {
public:
    FFmpegProcessor();
    ~FFmpegProcessor();

    bool initialize();
    void shutdown();

    VideoMetadata probeMedia(const std::string& path);

    bool generateProgressVideo(
        const std::string& output_path,
        SkiaRenderer* renderer,
        const std::vector<Chapter>& chapters,
        const RenderConfig& config,
        ProgressCallback callback
    );

    bool compositeVideos(
        const std::string& video_path,
        const std::string& overlay_path,
        const std::string& output_path,
        const RenderConfig& config,
        ProgressCallback callback
    );

private:
    bool openInputFile(AVFormatContext*& ctx, const std::string& path);
    bool openOutputFile(AVFormatContext*& ctx, const std::string& path,
                        int width, int height, int fps);

    bool encodeFrame(AVFormatContext* ctx, AVStream* stream,
                     AVCodecContext* codecCtx, AVFrame* frame);

    bool flushEncoder(AVFormatContext* ctx, AVStream* stream,
                      AVCodecContext* codecCtx);

    class Impl;
    std::unique_ptr<Impl> pImpl_;
};
```

进度条视频的生成采用时间轴驱动的方式。每一帧都对应一个特定的进度值，范围从 0.0 到 1.0。我们按照设定的帧率遍历整个时间轴，对每个时间点执行以下操作：计算当前进度值，调用 SkiaRenderer 渲染该时间点的进度条图像，将 Skia 图像转换为 FFmpeg 可以接受的帧格式，将帧编码并写入输出文件。这个过程在后台线程中执行，通过回调函数向调用者报告进度。

视频合成使用 FFmpeg 的滤镜链实现。对于每个视频帧，我们在时间轴上计算进度条覆盖层应该出现的水平位置，然后使用 overlay 滤镜将进度条叠加到原视频上。为了确保进度条覆盖层的尺寸与原视频匹配，我们预先根据原视频的分辨率计算进度条的合适高度和宽度。

## 4. FFmpeg 集成方案

### 4.1 FFmpeg 组件选择

FFmpeg 项目包含多个独立的库组件，在我们的应用中只需要其中一部分。libavformat 负责处理各种媒体容器的解封装和封装，支持 MP4、MKV、AVI 等常见格式。libavcodec 实现了大量的音视频编解码器，包括 H.264、H.265、VP9 等视频编码器和 AAC、MP3 等音频编码器。libavutil 提供工具函数，包括内存管理、数学运算、像素格式转换等。libavfilter 实现了强大的滤镜管线，支持视频缩放、叠加、颜色调整等操作。

我们不会直接使用 FFmpeg 的编解码器实现自己的视频编码，而是利用 FFmpeg 的命令行工具或高级 API 完成工作。对于进度条视频的生成，我们有两种技术路线可以选择。第一种是使用 libavformat 和 libavcodec 的 C API，需要手动管理编解码器上下文、帧缓冲区和数据包，工作量较大但灵活性高。第二种是使用 FFmpeg 的 filter graph API，将渲染好的帧通过管道送入 FFmpeg 进程，这种方式代码更简洁但需要进程间通信。

考虑到开发效率和稳定性，我们选择第一种方案，直接使用 FFmpeg 的 C API。这样做的好处是所有操作都在同一个进程内完成，避免了进程间通信的开销和复杂性，同时也便于集成错误处理和进度报告机制。

### 4.2 视频编码参数

进度条视频的编码参数需要精心选择，以平衡文件大小、画质和兼容性：

**视频编码器**选择 libx264，这是 H.264 编码的事实标准，具有极佳的兼容性，几乎所有播放设备都支持 H.264 格式。x264 编码器的 preset 参数控制编码速度和质量的对等，设置为 veryfast 可以在保证较快速度的同时获得不错的画质。CRF（Constant Rate Factor）值设置为 18，这是视觉无损和较高压缩率之间的平衡点。

**像素格式**使用 yuv420p，这是 H.264 标准要求的最基本格式，确保最大兼容性。如果使用更高精度的格式如 yuv422p 或 yuv444p，虽然可以减少色度采样损失，但会导致兼容性问题。

**音频处理**方面，进度条视频不包含音频轨道，因此不需要音频编码器。如果将来需要添加音频提示音，可以使用 libmp3lame 或 libfdk-aac 编码器。

**容器格式**选择 MP4，并添加 movflags +faststart 选项。这个选项将文件的 moov 原子移到文件开头，使得视频可以在完全下载之前开始播放，对于网络传输场景尤为重要。

### 4.3 进度条动画的 FFmpeg 实现

进度条动画的核心是在每个时间点计算进度条的填充进度。根据当前时间计算进度的公式是：progress = currentTime / totalDuration。然后将这个进度值转换为进度条覆盖层的 x 坐标偏移量。进度条覆盖层的初始位置使其右边缘与进度条背景的左边缘对齐，然后随着时间推移向左移动，直到完全覆盖整个背景。

使用 FFmpeg 的滤镜链实现这个效果的命令大致如下：

```
ffmpeg -i progress_bar_frames_%04d.png -i original_video.mp4 \
  -filter_complex "[0:v]fps=30[frames];[1:v]scale=1920:1080[video];
    [video][frames]overlay=x='min(0,W*t/T)':y=H-h[out]" \
  -map "[out]" -c:v libx264 -preset veryfast -crf 18 output.mp4
```

在我们的 C++ 实现中，这个滤镜链被翻译为 avfilter_graph_parse2 函数的参数。为了避免频繁创建和销毁滤镜图，我们会在初始化时创建一个滤镜图模板，然后在每帧处理时复用它。

## 5. 错误处理与资源管理

### 5.1 异常层次结构

我们定义了一套完整的异常层次结构，用于区分不同类型的错误：

```cpp
namespace progressbar {

class ProgressBarException : public std::runtime_error {
public:
    explicit ProgressBarException(const std::string& message,
                                  int error_code = 0)
        : std::runtime_error(message), errorCode_(error_code) {}

    int errorCode() const { return errorCode_; }

private:
    int errorCode_;
};

class InitializationException : public ProgressBarException {
public:
    explicit InitializationException(const std::string& message)
        : ProgressBarException(message, 2000) {}
};

class RenderException : public ProgressBarException {
public:
    explicit RenderException(const std::string& message)
        : ProgressBarException(message, 3000) {}
};

class VideoException : public ProgressBarException {
public:
    explicit VideoException(const std::string& message, int error_code = 0)
        : ProgressBarException(message, 3000 + error_code) {}
};

class ValidationException : public ProgressBarException {
public:
    explicit ValidationException(const std::string& message)
        : ProgressBarException(message, 1000) {}
};

} // namespace progressbar
```

每个异常类都关联一个错误码，错误码的百位数字表示错误类别。ValidationException 用于参数验证失败，InitializationException 用于模块初始化失败，RenderException 用于图像渲染错误，VideoException 用于视频处理错误。调用者可以根据错误码判断错误类型，采取相应的恢复措施。

### 5.2 资源包装类

为了确保资源的正确释放，我们定义了多个资源包装类，它们利用 C++ 的 RAII 机制自动管理资源生命周期：

```cpp
template<typename T, void(*Deleter)(T*)>
class UniquePtr {
public:
    explicit UniquePtr(T* ptr = nullptr) : ptr_(ptr) {}

    ~UniquePtr() {
        if (ptr_) Deleter(ptr_);
    }

    T* get() const { return ptr_; }
    T* operator->() const { return ptr_; }
    T& operator*() const { return *ptr_; }

    void reset(T* ptr = nullptr) {
        if (ptr_) Deleter(ptr_);
        ptr_ = ptr;
    }

    UniquePtr(const UniquePtr&) = delete;
    UniquePtr& operator=(const UniquePtr&) = delete;

private:
    T* ptr_;
};

// FFmpeg 类型特化
using AVFormatContextPtr = UniquePtr<AVFormatContext, avformat_close_input>;
using AVCodecContextPtr = UniquePtr<AVCodecContext, avcodec_free_context>;
using AVFramePtr = UniquePtr<AVFrame, av_frame_free>;
using AVPacketPtr = UniquePtr<AVPacket, av_packet_free>;
using SwsContextPtr = UniquePtr<SwsContext, sws_freeContext>;
```

这些包装类的设计参考了 C++ 标准库的 std::unique_ptr，但针对特定类型提供了自定义的删除器。对于 FFmpeg 的各种上下文和结构体，每个都有对应的释放函数，包装类确保这些释放函数在对象销毁时被正确调用。

### 5.3 内存管理策略

视频处理涉及大量的内存分配，包括帧缓冲区、缩放缓冲区、编码器输出缓冲区等。为了减少内存分配开销和提高缓存命中，我们采用以下策略：

**对象池模式**用于频繁创建和销毁的小对象，如 AVPacket 和 AVFrame。这些对象的创建和销毁开销虽然不大，但在处理数十万帧视频时会累积成可观的开销。对象池预先分配一批对象，需要时从池中获取，用完后归还池中而不是真正释放。

**预分配缓冲区**用于确定大小的缓冲区，如帧缓冲区和缩放缓冲区。在处理开始前根据视频分辨率预先分配好所有需要的缓冲区，处理过程中复用这些缓冲区，避免反复分配释放。

**内存对齐**对于 SIMD 优化的代码非常重要。我们使用 posix_memalign 或 aligned_alloc 确保缓冲区按适当的边界对齐，避免因内存不对齐导致的性能损失或崩溃。

## 6. 线程安全设计

### 6.1 并发模型

C++ 原生库在单线程环境中工作，由 UXP 的 JavaScript 主线程调用。JavaScript 到 C++ 的调用是串行化的，同一时刻只有一个调用在执行，因此我们不需要在库内部处理复杂的并发同步问题。然而，在处理过程中我们可能创建工作线程来执行耗时操作，这些工作线程需要遵循一些安全规则。

工作线程不应该调用任何 UXP API 或 JavaScript 回调函数，这些调用必须在主线程上执行。进度回调函数接收的参数也需要特别注意，因为回调函数可能捕获了 JavaScript 上下文，在工作线程中调用会导致未定义行为。我们的解决方案是将回调调用封装为异步任务，提交到主线程的执行队列中。

### 6.2 线程局部存储

某些资源天然不适合在多线程间共享，如 Skia 的 GPU 上下文、FFmpeg 的某些编解码器状态等。对于这类资源，我们使用线程局部存储（Thread Local Storage）来管理。每个线程维护自己独立的资源实例，线程结束时释放这些资源。

```cpp
thread_local std::unique_ptr<SkiaRenderer> threadRenderer;
thread_local std::vector<uint8_t> frameBuffer;

SkiaRenderer* getThreadRenderer() {
    if (!threadRenderer) {
        threadRenderer = std::make_unique<SkiaRenderer>();
        threadRenderer->initialize();
    }
    return threadRenderer.get();
}
```

## 7. 测试策略

### 7.1 单元测试

每个核心类都应有对应的单元测试，使用 Google Test 框架编写。测试覆盖以下方面：

**边界条件测试**验证代码在极端输入下的行为。例如，章节时间为负数或超出总时长、宽度或高度为零、颜色值为非法格式等情况下的处理。

**正确性测试**使用已知的输入和期望的输出验证功能的正确性。例如，使用特定的章节配置渲染进度条图像，然后与预先准备的标准图像逐像素比较。

**回归测试**确保代码修改不会破坏已有功能。每次提交都会运行完整的测试套件，任何测试失败都会阻止代码合并。

### 7.2 集成测试

集成测试验证各模块之间的协作是否正确。由于 FFmpeg 和 Skia 的依赖，集成测试需要在真实的系统环境中运行，不能使用 mock 对象。集成测试关注端到端的功能：从配置和章节数据开始，到生成可播放的视频文件结束。

### 7.3 性能基准测试

性能基准测试用于追踪优化效果和防止性能退化。我们定义了若干基准场景，如渲染 1080P 分辨率、10 分钟时长的进度条视频，测量执行时间和内存峰值。基准测试在 CI/CD 流程中定期运行，结果记录到数据库中，可以查看历史趋势。

## 8. 相关文档

- [系统架构文档](./architecture.md)
- [UXP UI 设计文档](./ui-design.md)
- [API 接口规范文档](./api-specification.md)
- [编译打包指南](./build-guide.md)