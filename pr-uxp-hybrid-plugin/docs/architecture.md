# 系统架构文档

## 1. 架构概述

### 1.1 整体架构

本项目采用 **UXP 混合插件架构**，将功能分为三个主要层次：

```
┌─────────────────────────────────────────────────────────────┐
│                    Premiere Pro 宿主                        │
│  ┌───────────────────────────────────────────────────────┐  │
│  │                  UXP 运行时环境                        │  │
│  │  ┌─────────────────────────────────────────────────┐  │  │
│  │  │              UI 层 (HTML/CSS/JS)                │  │  │
│  │  │  • Spectrum Widgets 组件                        │  │  │
│  │  │  • 章节管理界面                                  │  │  │
│  │  │  • 样式配置面板                                  │  │  │
│  │  │  • 实时预览（Canvas）                           │  │  │
│  │  └─────────────────────────────────────────────────┘  │  │
│  │                        │                               │  │
│  │                        │ JS 函数调用                   │  │
│  │                        ▼                               │  │
│  │  ┌─────────────────────────────────────────────────┐  │  │
│  │  │           JavaScript 逻辑层                      │  │  │
│  │  │  • 业务逻辑处理                                  │  │  │
│  │  │  • 数据验证和转换                                │  │  │
│  │  │  • Premiere API 集成                            │  │  │
│  │  │  • 原生模块调用封装                              │  │  │
│  │  └─────────────────────────────────────────────────┘  │  │
│  │                        │                               │  │
│  │                        │ require()                     │  │
│  │                        ▼                               │  │
│  │  ┌─────────────────────────────────────────────────┐  │  │
│  │  │        C++ 原生库层 (uxpaddon)                   │  │  │
│  │  │  • FFmpeg 视频处理                               │  │  │
│  │  │  • Skia 图像渲染                                 │  │  │
│  │  │  • 性能密集型计算                                │  │  │
│  │  └─────────────────────────────────────────────────┘  │  │
│  └───────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

### 1.2 数据流

```
用户输入 → UI 层验证 → JavaScript 逻辑处理 → C++ 原生处理 → 生成文件
    ↑                                                            │
    │                                                            ▼
    └──────────────────────────────────── 导入到 Premiere 序列 ←─┘
```

## 2. 模块划分

### 2.1 模块依赖图

```
┌──────────────┐
│   UI 模块    │ ◄── 用户交互入口
└──────┬───────┘
       │
       ▼
┌──────────────┐
│  业务逻辑模块 │ ◄── 章节管理、配置验证
└──────┬───────┘
       │
       ├──────────────────┐
       ▼                  ▼
┌──────────────┐    ┌──────────────┐
│ Premiere API │    │ 原生模块封装 │
│    模块      │    │     模块     │
└──────────────┘    └──────┬───────┘
                           │
                           ▼
                    ┌──────────────┐
                    │  FFmpeg 处理 │
                    │     模块     │
                    └──────────────┘
                           │
                           ▼
                    ┌──────────────┐
                    │ Skia 渲染    │
                    │     模块     │
                    └──────────────┘
```

### 2.2 模块职责

| 模块名称 | 职责 | 核心技术 |
|---------|------|---------|
| **UI 模块** | 用户界面渲染和交互 | HTML/CSS/Spectrum Widgets |
| **业务逻辑模块** | 章节管理、配置验证、数据转换 | JavaScript ES6+ |
| **Premiere API 模块** | 项目/序列操作、素材导入 | UXP DOM API |
| **原生模块封装** | C++ 模块加载和接口适配 | Node-API 风格接口 |
| **FFmpeg 处理模块** | 视频生成、合成、编码 | FFmpeg libav* |
| **Skia 渲染模块** | 进度条图像渲染 | Skia 2D Graphics |

## 3. 目录结构

```
pr-uxp-hybrid-plugin/
├── README.md
├── docs/
│   ├── architecture.md          # 本文档
│   ├── cpp-library-design.md    # C++ 原生库设计
│   ├── ui-design.md             # UI 设计
│   ├── api-specification.md     # API 接口规范
│   ├── tasks.md                 # 开发任务清单
│   └── build-guide.md           # 编译打包指南
├── src/
│   ├── plugin/                  # UXP 插件源码
│   │   ├── manifest.json        # 插件清单
│   │   ├── index.html           # 入口 HTML
│   │   ├── index.js             # 入口 JS
│   │   ├── styles/
│   │   │   └── main.css         # 主样式表
│   │   ├── components/
│   │   │   ├── ChapterManager.js
│   │   │   ├── StylePanel.js
│   │   │   └── PreviewCanvas.js
│   │   ├── services/
│   │   │   ├── PremiereService.js
│   │   │   ├── ProgressBarService.js
│   │   │   └── ConfigService.js
│   │   └── utils/
│   │       ├── validator.js
│   │       └── logger.js
│   └── native/                  # C++ 原生库源码
│       ├── CMakeLists.txt
│       ├── include/
│       │   ├── ffmpeg_processor.h
│       │   ├── skia_renderer.h
│       │   └── addon_main.h
│       ├── src/
│       │   ├── ffmpeg_processor.cpp
│       │   ├── skia_renderer.cpp
│       │   └── addon_main.cpp
│       └── third_party/
│           └── (依赖的第三方库)
├── test/
│   ├── unit/                    # 单元测试
│   └── integration/             # 集成测试
└── build/                       # 构建输出目录
    ├── macOS/
    ├── windows/
    └── package/                 # 打包输出
```

## 4. 核心类设计

### 4.1 JavaScript 层

#### ProgressBarService

```javascript
/**
 * 进度条生成服务
 * 负责协调 UI 和原生模块之间的交互
 */
class ProgressBarService {
    constructor() {
        this.processor = require("progress_processor.uxpaddon");
    }

    /**
     * 生成进度条图像
     * @param {Object} config - 生成配置
     * @returns {Promise<string>} 生成的文件路径
     */
    async generateImage(config) {
        this.validateConfig(config);
        const outputPath = await this.processor.generateImage(config);
        return outputPath;
    }

    /**
     * 生成进度条动画视频
     * @param {Array<Chapter>} chapters - 章节列表，时间格式为 H:MM:SS:FF
     * @param {Object} config - 生成配置
     * @returns {Promise<string>} 生成的文件路径
     */
    async generateVideo(chapters, config) {
        this.validateConfig(config);
        this.validateChapters(chapters);
        
        const internalChapters = chapters.map(ch => ({
            framePosition: this.parseTimecode(ch.time, config.fps),
            title: ch.title
        }));
        
        const outputPath = await this.processor.generateVideo(
            internalChapters,
            config
        );
        
        return outputPath;
    }

    /**
     * 合成视频（叠加进度条到原视频）
     * @param {string} videoPath - 原视频路径
     * @param {string} progressBarPath - 进度条视频路径
     * @param {Object} config - 合成配置
     * @returns {Promise<string>} 生成的文件路径
     */
    async compositeWithVideo(videoPath, progressBarPath, config) {
        const outputPath = await this.processor.compositeWithVideo(
            videoPath,
            progressBarPath,
            config
        );
        return outputPath;
    }

    /**
     * 解析时间码为帧位置
     * @param {string} timecode - 时间码，格式为 H:MM:SS:FF
     * @param {number} fps - 帧率
     * @returns {number} 帧位置
     */
    parseTimecode(timecode, fps) {
        const parts = timecode.split(':').map(Number);
        let frame = 0;
        
        if (parts.length === 2) {  // SS:FF
            frame = parts[0] * fps + parts[1];
        } else if (parts.length === 3) {  // MM:SS:FF
            frame = parts[0] * 60 * fps + parts[1] * fps + parts[2];
        } else if (parts.length === 4) {  // H:MM:SS:FF
            frame = parts[0] * 3600 * fps + parts[1] * 60 * fps + parts[2] * fps + parts[3];
        }
        
        return frame;
    }

    /**
     * 将帧位置格式化为时间码
     * @param {number} frame - 帧位置
     * @param {number} fps - 帧率
     * @returns {string} 时间码
     */
    formatTimecode(frame, fps) {
        const h = Math.floor(frame / (3600 * fps));
        const m = Math.floor((frame % (3600 * fps)) / (60 * fps));
        const s = Math.floor((frame % (60 * fps)) / fps);
        const f = frame % fps;
        
        const pad = (n) => String(n).padStart(2, '0');
        
        if (h > 0) {
            return `${h}:${pad(m)}:${pad(s)}:${pad(f)}`;
        }
        return `${m}:${pad(s)}:${pad(f)}`;
    }
}
```

#### PremiereService

```javascript
/**
 * Premiere API 服务
 * 封装 Premiere Pro UXP API 的常用操作
 */
class PremiereService {
    constructor() {
        this.app = require("premierepro");
    }

    /**
     * 获取当前活动序列
     * @returns {Promise<Sequence>}
     */
    async getActiveSequence() {
        const project = await this.app.Project.getActiveProject();
        return await project.getActiveSequence();
    }

    /**
     * 导入文件到项目
     * @param {Array<string>} filePaths - 文件路径列表
     * @returns {Promise<Array<Media>>}
     */
    async importFiles(filePaths) {
        const project = await this.app.Project.getActiveProject();
        return await project.importFiles(filePaths);
    }

    /**
     * 添加剪辑到轨道
     * @param {Track} track - 目标轨道
     * @param {Media} media - 媒体素材
     * @param {number} position - 放置位置（时间码）
     */
    async addClipToTrack(track, media, position) {
        await track.createClip(media, position);
    }
}
```

### 4.2 C++ 原生层

#### ProgressProcessor 类

```cpp
#pragma once

#include <string>
#include <vector>
#include <map>
#include <memory>

namespace progressbar {

struct Chapter {
    double time;
    std::string title;
};

struct RenderConfig {
    int width;
    int height;
    std::string bg_color;
    std::string text_color;
    std::string separator_color;
    int font_size;
    int separator_width;
    int fps;
    double total_duration;
};

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

## 5. 接口设计

### 5.1 JavaScript 到 C++ 的接口

```javascript
// 原生模块导出的接口
const progressProcessor = {
    // 初始化
    initialize: () => boolean,
    
    // 生成静态图像
    generateImage: (config: RenderConfig) => Promise<string>,
    
    // 生成动画视频
    generateVideo: (
        chapters: Chapter[],
        config: RenderConfig
    ) => Promise<string>,
    
    // 合成视频
    compositeWithVideo: (
        videoPath: string,
        overlayPath: string,
        config: RenderConfig
    ) => Promise<string>,
    
    // 获取视频信息
    getVideoInfo: (videoPath: string) => Promise<VideoInfo>,
    
    // 设置进度回调
    setProgressCallback: (callback: ProgressCallback) => void
};
```

### 5.2 数据类型定义

```typescript
// TypeScript 类型定义（供 IDE 自动补全）

interface Chapter {
    time: number;      // 时间点（秒）
    title: string;     // 章节标题
}

interface RenderConfig {
    width: number;           // 输出宽度
    height: number;          // 输出高度
    bg_color: string;        // 背景颜色 (hex)
    text_color: string;      // 文字颜色 (hex)
    separator_color: string; // 分隔线颜色 (hex)
    font_size: number;       // 字体大小
    separator_width: number; // 分隔线宽度
    fps: number;             // 帧率
    total_duration: number;  // 总时长（秒）
}

interface VideoInfo {
    width: number;
    height: number;
    fps: number;
    duration: number;
    codec: string;
}

type ProgressCallback = (progress: number) => void;
```

## 6. 错误处理

### 6.1 错误分类

| 错误类型 | 错误码 | 说明 |
|---------|--------|------|
| **验证错误** | 1000-1999 | 参数验证失败 |
| **初始化错误** | 2000-2999 | 模块初始化失败 |
| **处理错误** | 3000-3999 | 图像/视频处理失败 |
| **Premiere 错误** | 4000-4999 | Premiere API 调用失败 |
| **系统错误** | 5000-5999 | 文件系统、系统调用错误 |

### 6.2 错误处理流程

```
┌─────────────┐
│  发生错误   │
└──────┬──────┘
       │
       ▼
┌─────────────┐
│ 错误分类    │
└──────┬──────┘
       │
       ├── 参数验证 ──→ 返回友好错误信息
       │
       ├── 系统错误 ──→ 记录日志，尝试恢复
       │
       └── 处理错误 ──→ 清理临时文件，返回错误
```

## 7. 性能考量

### 7.1 性能优化策略

| 策略 | 说明 | 预期收益 |
|------|------|---------|
| **多线程处理** | FFmpeg 在独立线程运行 | UI 不阻塞 |
| **增量渲染** | 只重新渲染变化的部分 | 减少计算量 |
| **内存池** | 复用图像缓冲区 | 减少内存分配 |
| **流式处理** | 边读边写，减少内存占用 | 支持大文件 |
| **GPU 加速** | 使用 Skia GPU 后端 | 渲染加速 |

### 7.2 进度反馈

- 每秒至少更新一次进度
- 支持取消操作
- 显示预计剩余时间

## 8. 安全性考量

| 安全点 | 措施 |
|--------|------|
| **路径遍历** | 验证所有文件路径，禁止 `..` |
| **命令注入** | FFmpeg 参数使用白名单 |
| **内存安全** | 使用智能指针，避免泄漏 |
| **临时文件** | 使用安全随机命名，自动清理 |

## 9. 扩展性设计

### 9.1 模块化设计

- C++ 原生库可以独立编译和测试
- JavaScript 层不直接依赖 FFmpeg/Skia 实现细节
- 便于后续替换底层库（如从 Skia 切换到其他渲染库）

### 9.2 插件扩展点

- 支持自定义标记物（GIF/PNG）
- 支持自定义字体
- 支持输出格式扩展（GIF、WebP 等）

## 10. 相关文档

- [C++ 原生库设计文档](./cpp-library-design.md)
- [UXP UI 设计文档](./ui-design.md)
- [API 接口规范文档](./api-specification.md)
- [编译打包指南](./build-guide.md)