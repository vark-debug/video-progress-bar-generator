# API 接口规范文档

## 1. 接口设计概述

### 1.1 接口分层架构

本项目的 API 接口分为三个主要层次，每个层次承担不同的职责，层与层之间通过清晰定义的接口进行通信。最上层是展示层，由 HTML/CSS/JavaScript 编写，运行在 UXP 的 WebView 中，负责接收用户输入并展示处理结果。中间层是业务逻辑层，处理参数验证、数据转换和流程编排，协调上下两层的工作。最底层是原生处理层，由 C++ 编写，通过 UXP 混合插件机制暴露接口，负责完成图像渲染和视频编码等计算密集型任务。

```
┌─────────────────────────────────────────────┐
│              展示层 (UI Layer)               │
│  • 用户输入表单                              │
│  • 实时预览画布                              │
│  • 进度显示                                  │
│  • 错误提示                                  │
└──────────────────────┬──────────────────────┘
                       │ DOM 事件 / 函数调用
                       ▼
┌─────────────────────────────────────────────┐
│            业务逻辑层 (Service Layer)        │
│  • ProgressBarService                       │
│  • PremiereService                          │
│  • ConfigService                            │
│  • 参数验证与转换                            │
└──────────────────────┬──────────────────────┘
                       │ require() 模块加载
                       ▼
┌─────────────────────────────────────────────┐
│            原生处理层 (Native Layer)         │
│  • C++ uxpaddon 模块                        │
│  • FFmpeg 视频处理                           │
│  • Skia 图像渲染                             │
└─────────────────────────────────────────────┘
```

### 1.2 接口设计原则

在设计接口时，我们遵循以下原则以确保接口的可用性、稳定性和可维护性。首先是**最小化接口**原则，只暴露真正需要的函数和数据结构，避免过度抽象导致的复杂性。其次是**类型安全**原则，所有参数和返回值都应有明确的类型定义，JavaScript 端使用 TypeScript 辅助类型检查。第三是**向前兼容**原则，接口一旦发布就不能轻易改变，如果需要新增功能，通过添加新函数实现而非修改现有函数。第四是**错误透明**原则，所有可能失败的函数都应返回明确的错误信息，便于调用者进行错误处理和用户提示。

## 2. 原生模块接口规范

### 2.1 模块加载方式

C++ 原生库通过 UXP 的 require 机制加载，模块名称为 `progress_processor.uxpaddon`。加载后返回一个包含所有导出函数和类的对象。由于 UXP 的模块系统遵循 CommonJS 规范，加载操作是同步的。

```javascript
// 加载原生模块
const processor = require("progress_processor.uxpaddon");

// 检查模块是否正确加载
if (!processor || !processor.ProgressProcessor) {
    throw new Error("原生模块加载失败");
}
```

### 2.2 ProgressProcessor 类接口

ProgressProcessor 是原生模块的核心类，提供进度条生成的所有功能。

#### 构造函数

```javascript
/**
 * 创建进度条处理器实例
 * @constructor
 */
new ProgressProcessor()
```

#### 初始化方法

```javascript
/**
 * 初始化原生模块
 * 在使用其他功能前必须调用此方法
 * @returns {boolean} 初始化是否成功
 * @throws {InitializationError} 初始化失败时抛出
 */
processor.initialize()
```

#### 图像生成方法

```javascript
/**
 * 生成进度条静态图像
 * @param {string} outputPath - 输出文件路径（PNG 格式）
 * @param {Chapter[]} chapters - 章节列表
 * @param {RenderConfig} config - 渲染配置
 * @returns {Promise<string>} 生成的文件路径
 * @throws {ValidationError} 参数验证失败
 * @throws {RenderError} 渲染过程出错
 */
async processor.generateImage(outputPath, chapters, config)
```

#### 视频生成方法

```javascript
/**
 * 生成进度条动画视频
 * @param {string} outputPath - 输出文件路径（MP4 格式）
 * @param {Chapter[]} chapters - 章节列表
 * @param {RenderConfig} config - 渲染配置
 * @param {ProgressCallback} onProgress - 进度回调函数
 * @returns {Promise<string>} 生成的文件路径
 * @throws {ValidationError} 参数验证失败
 * @throws {VideoError} 视频生成过程出错
 */
async processor.generateVideo(outputPath, chapters, config, onProgress)
```

#### 视频合成方法

```javascript
/**
 * 将进度条叠加到原视频
 * @param {string} videoPath - 原视频路径
 * @param {string} overlayPath - 进度条视频路径
 * @param {string} outputPath - 输出文件路径
 * @param {CompositeConfig} config - 合成配置
 * @param {ProgressCallback} onProgress - 进度回调函数
 * @returns {Promise<string>} 生成的文件路径
 * @throws {ValidationError} 参数验证失败
 * @throws {VideoError} 视频合成过程出错
 */
async processor.compositeWithVideo(videoPath, overlayPath, outputPath, config, onProgress)
```

#### 视频信息查询方法

```javascript
/**
 * 获取视频文件的元信息
 * @param {string} videoPath - 视频文件路径
 * @returns {Promise<VideoInfo>} 视频元信息
 * @throws {ValidationError} 文件路径无效
 * @throws {VideoError} 无法读取视频信息
 */
async processor.getVideoInfo(videoPath)
```

#### 关闭方法

```javascript
/**
 * 释放原生模块占用的资源
 * 在插件关闭时应调用此方法
 */
processor.shutdown()
```

### 2.3 数据类型定义

#### Chapter 章节结构

```typescript
/**
 * 进度条章节
 * @typedef {Object} Chapter
 * @property {string} time - 章节开始时间（帧级精度），格式为 H:MM:SS:FF
 * @property {string} title - 章节标题，支持多行文本
 */
interface Chapter {
    time: string;  // 格式: "H:MM:SS:FF"，例如 "0:01:05:12" 表示第1分5秒第12帧
    title: string;
}
```

**字段说明：**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| time | string | 是 | 章节开始时间，格式为 `H:MM:SS:FF`，其中 FF 表示帧号（基于序列帧率）。例如 `1:05:12` 表示 1小时5分12秒0帧，`0:01:05:12` 表示 1分5秒第12帧。当帧率大于等于 100 时，FF 部分可能为两位或三位数字。 |
| title | string | 是 | 章节标题文本，最大长度为 200 字符。支持换行符 `\n` 进行多行显示。 |

**验证规则：**

- time 格式必须符合 `H:MM:SS:FF` 或 `MM:SS:FF` 或 `SS:FF` 模式
- FF（帧号）必须小于当前序列的帧率
- time 转换后的帧位置必须大于等于 0
- time 转换后的帧位置应该小于等于总帧数
- title 不能为空字符串
- title 的长度不能超过 200 字符

**时间格式说明：**

Premiere Pro 是帧级精度的视频编辑软件，本插件采用与 PR 一致的时间格式，确保时间的精确表示和 Seamless Integration（无缝集成）。

| 格式示例 | 含义 | 说明 |
|---------|------|------|
| `12` | SS:FF | 12秒0帧 |
| `1:05` | MM:SS:FF | 1分5秒0帧 |
| `1:05:12` | MM:SS:FF | 1分5秒12帧 |
| `0:01:05:12` | H:MM:SS:FF | 1分5秒12帧（显式小时） |
| `1:00:05:12` | H:MM:SS:FF | 1小时5秒12帧 |

**内部存储与转换：**

在 API 内部，所有时间值仍然以帧数（number 类型）存储和计算，字符串格式仅用于用户界面展示和输入。这种设计确保计算的精确性，同时提供用户友好的时间表示。

```typescript
// 内部时间表示（帧数）
interface InternalChapter {
    framePosition: number;  // 帧位置（整数）
    title: string;
}

// API 转换函数
function parseTimecode(timecode: string, fps: number): number {
    // 将 H:MM:SS:FF 转换为帧数
    const parts = timecode.split(':').map(Number);
    let framePosition = 0;
    
    if (parts.length === 2) {  // SS:FF
        framePosition = parts[0] * fps + parts[1];
    } else if (parts.length === 3) {  // MM:SS:FF
        framePosition = parts[0] * 60 * fps + parts[1] * fps + parts[2];
    } else if (parts.length === 4) {  // H:MM:SS:FF
        framePosition = parts[0] * 3600 * fps + parts[1] * 60 * fps + parts[2] * fps + parts[3];
    }
    
    return framePosition;
}

function formatTimecode(framePosition: number, fps: number): string {
    // 将帧数转换为 H:MM:SS:FF
    const hours = Math.floor(framePosition / (3600 * fps));
    const minutes = Math.floor((framePosition % (3600 * fps)) / (60 * fps));
    const seconds = Math.floor((framePosition % (60 * fps)) / fps);
    const frames = framePosition % fps;
    
    if (hours > 0) {
        return `${hours}:${String(minutes).padStart(2, '0')}:${String(seconds).padStart(2, '0')}:${String(frames).padStart(2, '0')}`;
    }
    return `${minutes}:${String(seconds).padStart(2, '0')}:${String(frames).padStart(2, '0')}`;
}
```

#### RenderConfig 渲染配置

```typescript
/**
 * 进度条渲染配置
 * @typedef {Object} RenderConfig
 */
interface RenderConfig {
    width: number;           // 输出宽度（像素）
    height: number;          // 输出高度（像素）
    bgColor: string;         // 背景颜色（HEX 格式，如 #FFFFFF）
    textColor: string;       // 文字颜色（HEX 格式）
    separatorColor: string;  // 分隔线颜色（HEX 格式）
    fontSize: number;        // 字体大小（像素）
    separatorWidth: number;  // 分隔线宽度（像素）
    fps: number;             // 帧率（每秒帧数）
    totalFrames: number;     // 总时长（帧数）
    fontPath?: string;       // 自定义字体文件路径（可选）
}
```

**字段说明：**

| 字段 | 类型 | 默认值 | 有效范围 | 说明 |
|------|------|--------|---------|------|
| width | number | 1920 | 320-7680 | 输出图像的宽度 |
| height | number | 90 | 36-720 | 输出图像的高度 |
| bgColor | string | #FFFFFF | #RRGGBB | 进度条背景颜色 |
| textColor | string | #111827 | #RRGGBB | 章节标题文字颜色 |
| separatorColor | string | #111827 | #RRGGBB | 章节分隔线颜色 |
| fontSize | number | 24 | 8-96 | 章节标题的字体大小 |
| separatorWidth | number | 8 | 1-40 | 章节分隔线的宽度 |
| fps | number | 30 | 1-120 | 生成视频的帧率 |
| totalFrames | number | 18000 | >0 | 视频总时长（帧数）。例如 30fps 的 10 分钟视频，totalFrames = 30 * 60 * 10 = 18000 |
| fontPath | string | 系统默认 | 有效字体文件路径 | 自定义字体文件路径 |

#### CompositeConfig 合成配置

```typescript
/**
 * 视频合成配置
 * @typedef {Object} CompositeConfig
 */
interface CompositeConfig {
    positionY: number;       // 进度条在视频中的垂直位置
    scale: number;           // 进度条相对于原视频的缩放比例
    opacity: number;         // 进度条叠加层的不透明度（0-1）
}
```

**字段说明：**

| 字段 | 类型 | 默认值 | 有效范围 | 说明 |
|------|------|--------|---------|------|
| positionY | number | 底部 | 0-1 | 进度条在视频中的垂直位置，0 表示顶部，1 表示底部 |
| scale | number | 1.0 | 0.1-2.0 | 进度条相对于原视频宽度的缩放比例 |
| opacity | number | 1.0 | 0-1 | 叠加层的不透明度，0 表示完全透明，1 表示完全不透明 |

#### VideoInfo 视频信息

```typescript
/**
 * 视频元信息
 * @typedef {Object} VideoInfo
 */
interface VideoInfo {
    width: number;       // 视频宽度（像素）
    height: number;      // 视频高度（像素）
    fps: number;         // 视频帧率
    duration: number;    // 视频时长（秒）
    codec: string;       // 视频编码格式
}
```

#### ProgressCallback 进度回调

```typescript
/**
 * 进度回调函数类型
 * @callback ProgressCallback
 * @param {number} progress - 当前进度（0-100）
 */
type ProgressCallback = (progress: number) => void;
```

**调用规则：**

- 进度值范围为 0 到 100 的整数或小数
- 开始时调用 progress(0)
- 过程中逐步增加到接近 100
- 完成后调用 progress(100)
- 至少每秒调用一次

### 2.4 错误类型定义

```typescript
/**
 * 错误类型枚举
 * @readonly
 * @enum {string}
 */
const ErrorType = {
    VALIDATION: "ValidationError",      // 参数验证错误
    INITIALIZATION: "InitializationError", // 初始化错误
    RENDER: "RenderError",              // 渲染错误
    VIDEO: "VideoError",                // 视频处理错误
    SYSTEM: "SystemError"               // 系统错误
};

/**
 * 错误码定义
 * @readonly
 */
const ErrorCode = {
    // 验证错误 (1000-1999)
    INVALID_CHAPTERS: 1001,         // 章节列表无效
    INVALID_TIME: 1002,             // 时间值无效
    INVALID_COLOR: 1003,            // 颜色值格式错误
    INVALID_DIMENSION: 1004,        // 尺寸参数无效
    INVALID_PATH: 1005,             // 文件路径无效

    // 初始化错误 (2000-2999)
    FFMPEG_INIT_FAILED: 2001,       // FFmpeg 初始化失败
    SKIA_INIT_FAILED: 2002,         // Skia 初始化失败
    FONT_LOAD_FAILED: 2003,         // 字体加载失败

    // 渲染错误 (3000-3999)
    RENDER_FAILED: 3001,            // 图像渲染失败
    ENCODE_FAILED: 3002,            // 视频编码失败

    // 系统错误 (5000-5999)
    FILE_WRITE_FAILED: 5001,        // 文件写入失败
    FILE_READ_FAILED: 5002,         // 文件读取失败
    OUT_OF_MEMORY: 5003             // 内存不足
};
```

### 2.5 错误对象结构

```typescript
/**
 * 错误对象结构
 * @typedef {Object} NativeError
 */
interface NativeError {
    type: string;       // 错误类型
    code: number;       // 错误码
    message: string;    // 错误消息（中文，便于用户理解）
    details?: string;   // 详细信息（用于调试）
}
```

**示例错误对象：**

```json
{
    "type": "ValidationError",
    "code": 1001,
    "message": "章节列表不能为空",
    "details": "chapters 参数至少需要包含一个有效的章节"
}
```

## 3. JavaScript 服务层接口

### 3.1 ProgressBarService

ProgressBarService 是 JavaScript 端的进度条生成服务，封装了与原生模块的交互逻辑。

```javascript
/**
 * 进度条生成服务
 */
class ProgressBarService {
    /**
     * @param {ProgressCallback} onProgress - 全局进度回调
     */
    constructor(onProgress = null) {
        this.processor = null;
        this.onProgress = onProgress;
    }

    /**
     * 初始化服务
     * @returns {Promise<void>}
     */
    async initialize() {
        // 加载原生模块
        const module = require("progress_processor.uxpaddon");
        this.processor = new module.ProgressProcessor();
        
        // 初始化原生模块
        const success = this.processor.initialize();
        if (!success) {
            throw new Error("原生模块初始化失败");
        }
    }

    /**
     * 生成进度条图像
     * @param {Chapter[]} chapters - 章节列表
     * @param {RenderConfig} config - 渲染配置
     * @returns {Promise<string>} 生成的文件路径
     */
    async generateImage(chapters, config) {
        this.validateChapters(chapters);
        this.validateConfig(config);
        
        const outputPath = this.getTempFilePath("progress_bar.png");
        return await this.processor.generateImage(outputPath, chapters, config);
    }

    /**
     * 生成进度条视频
     * @param {Chapter[]} chapters - 章节列表
     * @param {RenderConfig} config - 渲染配置
     * @returns {Promise<string>} 生成的文件路径
     */
    async generateVideo(chapters, config) {
        this.validateChapters(chapters);
        this.validateConfig(config);
        
        const outputPath = this.getTempFilePath("progress_bar.mp4");
        const progressCallback = (progress) => {
            if (this.onProgress) {
                this.onProgress(progress);
            }
        };
        
        return await this.processor.generateVideo(
            outputPath, 
            chapters, 
            config, 
            progressCallback
        );
    }

    /**
     * 合成视频
     * @param {string} videoPath - 原视频路径
     * @param {string} progressBarPath - 进度条视频路径
     * @param {CompositeConfig} compositeConfig - 合成配置
     * @param {RenderConfig} renderConfig - 渲染配置
     * @returns {Promise<string>} 生成的文件路径
     */
    async compositeWithVideo(videoPath, progressBarPath, compositeConfig, renderConfig) {
        const outputPath = this.getTempFilePath("final_video.mp4");
        const progressCallback = (progress) => {
            if (this.onProgress) {
                this.onProgress(progress);
            }
        };
        
        return await this.processor.compositeWithVideo(
            videoPath,
            progressBarPath,
            outputPath,
            compositeConfig,
            progressCallback
        );
    }

    /**
     * 获取视频信息
     * @param {string} videoPath - 视频文件路径
     * @returns {Promise<VideoInfo>}
     */
    async getVideoInfo(videoPath) {
        return await this.processor.getVideoInfo(videoPath);
    }

    /**
     * 释放资源
     */
    shutdown() {
        if (this.processor) {
            this.processor.shutdown();
            this.processor = null;
        }
    }

    // 私有方法
    private validateChapters(chapters) { /* ... */ }
    private validateConfig(config) { /* ... */ }
    private getTempFilePath(filename) { /* ... */ }
}
```

### 3.2 PremiereService

PremiereService 封装了 Premiere Pro UXP API 的常用操作。

```javascript
const app = require("premierepro");

/**
 * Premiere Pro API 服务
 */
class PremiereService {
    /**
     * 获取当前活动项目
     * @returns {Promise<Project>}
     */
    async getActiveProject() {
        return await app.Project.getActiveProject();
    }

    /**
     * 获取当前活动序列
     * @returns {Promise<Sequence>}
     */
    async getActiveSequence() {
        const project = await this.getActiveProject();
        return await project.getActiveSequence();
    }

    /**
     * 导入文件到项目
     * @param {string[]} filePaths - 文件路径数组
     * @returns {Promise<Media[]>}
     */
    async importFiles(filePaths) {
        const project = await this.getActiveProject();
        return await project.importFiles(filePaths);
    }

    /**
     * 添加素材到序列轨道
     * @param {Media} media - 媒体素材
     * @param {Track} track - 目标轨道
     * @param {number} position - 放置位置（时间码）
     * @returns {Promise<Clip>}
     */
    async addToSequence(media, track, position = 0) {
        return await track.createClip(media, position);
    }

    /**
     * 获取序列的视频轨道
     * @param {number} index - 轨道索引（从 0 开始）
     * @returns {Promise<Track>}
     */
    async getVideoTrack(index = 0) {
        const sequence = await this.getActiveSequence();
        return sequence.videoTracks[index];
    }

    /**
     * 获取序列属性
     * @returns {Promise<Object>}
     */
    async getSequenceProperties() {
        const sequence = await this.getActiveSequence();
        return {
            width: sequence.frameWidth,
            height: sequence.frameHeight,
            fps: sequence.frameRate,
            duration: sequence.duration
        };
    }
}
```

### 3.3 ConfigService

ConfigService 负责配置的持久化和默认值管理。

```javascript
/**
 * 配置服务
 */
class ConfigService {
    constructor() {
        this.storage = require("uxp").storage;
        this.configKey = "progress-bar-config";
    }

    /**
     * 获取保存的配置
     * @returns {Promise<RenderConfig>}
     */
    async loadConfig() {
        const savedConfig = await this.storage.localStorage.getItem(this.configKey);
        if (savedConfig) {
            return { ...this.getDefaultConfig(), ...JSON.parse(savedConfig) };
        }
        return this.getDefaultConfig();
    }

    /**
     * 保存配置
     * @param {RenderConfig} config
     */
    async saveConfig(config) {
        await this.storage.localStorage.setItem(
            this.configKey, 
            JSON.stringify(config)
        );
    }

    /**
     * 获取默认配置
     * @returns {RenderConfig}
     */
    getDefaultConfig() {
        return {
            width: 1920,
            height: 90,
            bgColor: "#FFFFFF",
            textColor: "#111827",
            separatorColor: "#111827",
            fontSize: 24,
            separatorWidth: 8,
            fps: 30,
            totalDuration: 600,
            fontPath: ""
        };
    }

    /**
     * 重置为默认配置
     */
    async resetConfig() {
        await this.saveConfig(this.getDefaultConfig());
    }
}
```

## 4. 事件接口规范

### 4.1 事件类型定义

```typescript
/**
 * 事件类型枚举
 */
const EventType = {
    // 进度条生成事件
    GENERATION_START: "progressbar:generation:start",
    GENERATION_PROGRESS: "progressbar:generation:progress",
    GENERATION_COMPLETE: "progressbar:generation:complete",
    GENERATION_ERROR: "progressbar:generation:error",
    
    // Premiere 事件
    PROJECT_CHANGED: "premiere:project:changed",
    SEQUENCE_CHANGED: "premiere:sequence:changed",
    
    // UI 事件
    CHAPTER_ADDED: "ui:chapter:added",
    CHAPTER_REMOVED: "ui:chapter:removed",
    CONFIG_CHANGED: "ui:config:changed"
};
```

### 4.2 事件对象结构

```typescript
/**
 * 事件对象基类
 */
interface BaseEvent {
    type: string;       // 事件类型
    timestamp: number;  // 事件时间戳
    source: string;     // 事件来源
}

/**
 * 生成进度事件
 */
interface GenerationProgressEvent extends BaseEvent {
    type: "progressbar:generation:progress";
    progress: number;   // 0-100
    stage: "rendering" | "encoding" | "compositing";
}

/**
 * 生成完成事件
 */
interface GenerationCompleteEvent extends BaseEvent {
    type: "progressbar:generation:complete";
    outputPath: string;
    duration: number;   // 生成耗时（毫秒）
}

/**
 * 生成错误事件
 */
interface GenerationErrorEvent extends BaseEvent {
    type: "progressbar:generation:error";
    error: NativeError;
}
```

### 4.3 事件总线

```javascript
/**
 * 简单的事件总线实现
 */
class EventBus {
    constructor() {
        this.listeners = new Map();
    }

    /**
     * 订阅事件
     * @param {string} eventType - 事件类型
     * @param {Function} callback - 回调函数
     * @returns {Function} 取消订阅的函数
     */
    on(eventType, callback) {
        if (!this.listeners.has(eventType)) {
            this.listeners.set(eventType, new Set());
        }
        this.listeners.get(eventType).add(callback);
        
        // 返回取消订阅函数
        return () => {
            this.listeners.get(eventType).delete(callback);
        };
    }

    /**
     * 触发事件
     * @param {BaseEvent} event - 事件对象
     */
    emit(event) {
        const callbacks = this.listeners.get(event.type);
        if (callbacks) {
            callbacks.forEach(callback => callback(event));
        }
    }

    /**
     * 取消订阅所有事件
     */
    offAll() {
        this.listeners.clear();
    }
}

// 全局事件总线实例
const eventBus = new EventBus();
```

## 5. 文件路径规范

### 5.1 路径约定

所有文件路径都使用绝对路径。原生模块需要知道文件的完整路径才能正确读写。在 JavaScript 层获取文件路径时，应使用 UXP 的文件系统 API。

```javascript
const { folder, file } = require("uxp").storage;

// 获取临时文件夹路径
const tempFolder = folder.cache;
// 或使用文档文件夹
const docsFolder = folder.documents;

// 构建文件路径
const outputPath = `${tempFolder}/${uuid()}.mp4`;
```

### 5.2 临时文件管理

处理过程中产生的临时文件应遵循以下管理策略：

| 文件类型 | 存放位置 | 清理时机 |
|---------|---------|---------|
| 输入文件副本 | cache 文件夹 | 处理完成后立即删除 |
| 进度条图像 | cache 文件夹 | 处理完成后立即删除 |
| 进度条视频 | cache 文件夹 | 导入到序列后删除 |
| 最终输出 | documents 文件夹 | 用户手动删除或自动清理 |

## 6. 版本兼容性

### 6.1 API 版本策略

接口采用语义化版本号（SemVer），格式为 `主版本.次版本.修订号`。主版本号递增表示有破坏性变更，次版本号递增表示新增功能，修订号递增表示缺陷修复。

当前版本：**1.0.0**

### 6.2 向后兼容性保证

- 不会删除已发布的公共接口
- 不会修改已有接口的参数类型和返回值类型
- 不会改变已有接口的语义
- 新增的接口将以新函数或新参数的形式添加
- 过时的接口会标记为 deprecated，但至少保留两个次版本

### 6.3 版本检测

JavaScript 代码可以通过检查原生模块的版本属性来确认兼容的 API 版本：

```javascript
const processor = require("progress_processor.uxpaddon");

if (processor.API_VERSION && processor.API_VERSION >= "1.0.0") {
    // 使用 1.0.0 及以上版本的 API
} else {
    throw new Error("原生模块版本过低，请更新插件");
}
```

## 7. 相关文档

- [系统架构文档](./architecture.md)
- [C++ 原生库设计文档](./cpp-library-design.md)
- [UXP UI 设计文档](./ui-design.md)
- [编译打包指南](./build-guide.md)