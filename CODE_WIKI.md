# 视频进度条生成器 - Code Wiki

## 1. 项目概述

### 1.1 项目简介

视频进度条生成器（Timeline Bar Studio）是一个用于生成视频章节进度条图片和动画视频的本地 Web 工具。支持导入用户视频，将进度条叠加在视频底部，并自动根据视频分辨率调整进度条尺寸。

**核心功能**：
- 生成静态/动态进度条图片
- 生成进度条动画视频
- 导入用户视频并合并进度条
- 仅生成纯进度条动画视频
- 自动分辨率适配（宽度/1920*90 = 进度条高度）
- 自动字号适配（28 * 宽度/1920）
- 拖拽导入视频、章节快捷添加
- GIF 标记动画
- 空格键控制视频播放/暂停

### 1.2 技术栈

| 层级 | 技术选型 |
|------|----------|
| 后端框架 | Flask 3.x |
| 图像处理 | Pillow (PIL) |
| 视频处理 | FFmpeg (via imageio-ffmpeg) |
| 前端框架 | 原生 HTML/CSS/JavaScript |
| 视频播放器 | Video.js 8.x |
| 桌面封装 | pywebview |
| 构建工具 | PyInstaller |

### 1.3 项目结构

```
视频进度条生成器/
├── app.py              # 核心 Flask 应用
├── app_webview.py      # 桌面窗口版本启动器
├── launcher.py         # 浏览器版本启动器
├── requirements.txt    # Python 依赖
├── video-progress-bar-webview.spec  # PyInstaller 打包配置
├── templates/
│   └── index.html      # 主页面模板
├── static/
│   ├── style.css       # 样式表
│   └── script.js       # 前端交互逻辑
├── custom_gifs/        # 用户上传的 GIF 文件目录
├── dist/               # PyInstaller 打包输出 (~120MB)
└── build/              # 构建临时文件
```

---

## 2. 核心模块说明

### 2.1 app.py - 核心后端模块

**职责**：提供所有 API 接口，处理图片生成、视频渲染、配置管理等核心业务逻辑。

#### 2.1.1 路径与目录管理

| 函数/变量 | 说明 |
|-----------|------|
| `APP_DIR` | 脚本所在目录（源码模式） |
| `BUNDLE_DIR` | PyInstaller 打包后的资源目录（`_MEIPASS`） |
| `RUNTIME_DIR` | 运行时目录（打包模式为可执行文件目录，源码模式为脚本目录） |
| `RESOURCE_DIR` | 实际使用的资源目录（优先使用外部目录，否则回退到打包目录） |
| `USER_DATA_DIR` | 用户数据目录（macOS: `~/Library/Application Support/视频进度条生成器`） |
| `CUSTOM_GIF_DIR` | 用户上传的 GIF 文件存储目录 |
| `OUTPUT_DIR` | 视频输出目录 |

#### 2.1.2 配置管理

**`load_config()`**
- 读取 `config.json` 配置文件
- 返回包含 `output_dir`、`font_path`、`font_name` 的字典

**`save_config(config: dict)`**
- 将配置保存到 `config.json`
- 使用 UTF-8 编码，格式化输出

**`get_output_dir()` / `set_output_dir(path: str)`**
- 获取/设置视频输出目录
- 支持用户自定义，默认输出到 `~/Documents/视频进度条生成器`

**`get_font_setting()` / `set_font_setting(font_path, font_name)`**
- 获取/设置当前使用的字体

#### 2.1.3 系统字体扫描

**`scan_system_fonts()` → `list[dict]`**

扫描系统字体目录，返回字体列表：

```python
{
    "name": "字体名称",
    "path": "/path/to/font.ttf",
    "source": "system"
}
```

- **macOS** 扫描目录：`/System/Library/Fonts`、`/Library/Fonts`、`~/Library/Fonts`
- **Windows** 扫描目录：`C:\Windows\Fonts`
- 支持格式：`.ttf`、`.otf`、`.ttc`

#### 2.1.4 字体风险检测

**`is_risky_font(font_name: str) → bool`**

检测字体是否为存在版权风险的苹果系统字体（PingFang、SF Pro 等）。

**风险字体列表**：
- PingFang SC/TC/HK
- SF Pro Display/Text
- Heiti
- Songti
- STXihei
- STHeiti
- Hiragino Sans GB

---

### 2.2 ProgressBarCreator 类

进度条生成器的核心类，负责图片渲染和视频编码。

#### 2.2.1 初始化

```python
class ProgressBarCreator:
    def __init__(self, custom_font_path: str = None)
```

- 如果提供了自定义字体路径且文件存在，使用该字体
- 否则调用 `find_font_path()` 自动查找合适字体

#### 2.2.2 字体查找

**`find_font_path() → Path | None`**

按优先级查找可用字体：

1. **macOS**：
   - 扫描系统字体目录
   - 优先使用 PingFang 系列字体
   - 其次使用 Heiti/Songti/YaHei 等中文字体
   - 返回找到的第一个匹配字体

2. **环境变量**：`FONT_PATH`

3. **本地目录**：
   - `static/`
   - `static/fonts/`
   - Windows 系统字体目录

4. **均未找到**：返回 `None`，使用 Pillow 默认字体

#### 2.2.3 时间处理

**`parse_time(value: str | int | float, fps: int = 30) → float`**

解析时间字符串为秒数，支持帧数：

| 输入格式 | 示例 | fps=30时输出 |
|----------|------|--------------|
| 秒数 | `"255"` | `255.0` |
| 分:秒 | `"4:15"` | `255.0` |
| 时:分:秒 | `"1:04:15"` | `3855.0` |
| **时:分:秒:帧** | `"00:01:01:08"` | `61.27` |

**`format_time(seconds: float) → str`**

将秒数格式化为时间字符串（统一使用 HH:MM:SS:FF 格式）：

- `3661.27` → `"01:01:01:08"`

#### 2.2.4 章节规范化

**`normalize_chapters(total_duration: float, chapters: list[dict], fps: int = 30) → list[Chapter]`**

处理章节数据：
1. 解析每个章节的时间点
2. 校验时间不超出总时长
3. 按时间排序
4. 如果第一个章节不是从 0 开始，自动在 0 位置插入

```python
@dataclass(frozen=True)
class Chapter:
    time: float      # 时间点（秒）
    title: str       # 章节标题
```

#### 2.2.5 文字换行

**`wrap_title(draw, text, font, max_width, max_lines=3) → list[str]`**

将长文本智能换行以适应指定宽度：
- 逐字符检测宽度
- 最多支持 3 行
- 最后一行超长时截断并添加 `...`

#### 2.2.6 静态进度条绘制

**`draw_static_bar(...) → Image.Image`**

生成章节进度条图片：

| 参数 | 类型 | 说明 |
|------|------|------|
| `total_duration` | str/int/float | 总时长 |
| `chapters` | list[dict] | 章节列表 |
| `width` | int | 图片宽度（320-7680） |
| `height` | int | 图片高度（36-720） |
| `bg_color` | str | 背景颜色（支持 "transparent"） |
| `text_color` | str | 文字颜色 |
| `separator_color` | str | 分割线颜色 |
| `separator_width` | int | 分割线粗细（1-40） |
| `font_size` | int | 字号 |
| `fps` | int | 帧率（用于解析带帧的时间） |

**渲染流程**：
1. 解析总时长，校验有效性
2. 规范化章节数据
3. 创建 RGBA 图像
4. 根据章节时间点计算 x 坐标位置
5. 绘制分割线
6. 在每个章节区域绘制标题文字（自动换行、自适应字号）

#### 2.2.7 图片转 Data URL

**`image_to_data_url(image: Image.Image) → str`**

将 PIL Image 转换为 Base64 编码的 Data URL，用于前端预览展示。

#### 2.2.8 FFmpeg 查找

**`find_ffmpeg() → str | None`**

按优先级查找 FFmpeg 可执行文件：

1. 环境变量 `FFMPEG_PATH`
2. `imageio_ffmpeg.get_ffmpeg_exe()`
3. 打包目录下的 `bin/ffmpeg`
4. 系统 PATH 中的 ffmpeg
5. 常见的打包目录位置

#### 2.2.9 GIF 标记解析

**`resolve_marker_gif(marker: str | None) → Path | None`**

解析 GIF 标记参数：
- `"none"` → 返回 `None`
- `"custom:filename.gif"` → 从 `CUSTOM_GIF_DIR` 加载

#### 2.2.10 视频生成

**`create_video(data: dict, chapters: list[dict], progress_callback=None, user_video_path: str = None) → Path`**

生成 MP4 视频文件：

| 参数 | 说明 |
|------|------|
| `data` | 包含 width、height、fps、colors、video_name 等配置 |
| `chapters` | 章节列表 |
| `progress_callback` | 进度回调函数，接收 0-100 的百分比 |
| `user_video_path` | 用户视频路径（可选，用于合并模式） |

**输出文件名**：
- 如果 `data.video_name` 存在：`<video_name>_进度条.mp4`
- 否则：`<job_id>.mp4`

**视频生成流程**：

1. **查找 FFmpeg**
2. **解析参数**：宽高、帧率、颜色、透明度、标记 GIF 等
3. **渲染底图**：调用 `draw_static_bar()` 生成高分辨率静态图（2x 缩放）
4. **构建 FFmpeg 命令**：

```
┌─────────────────────────────────────────────────────────────┐
│ 输入 0: 章节进度条 PNG 图片（静态底图）                       │
├─────────────────────────────────────────────────────────────┤
│ 输入 1: lavfi 颜色源（进度覆盖层）                           │
│         颜色=progress_color，大小=工作尺寸，时长=总时长         │
├─────────────────────────────────────────────────────────────┤
│ 输入 2 (可选): 标记 GIF 文件                                 │
└─────────────────────────────────────────────────────────────┘

滤镜链:
1. 底图 → fps滤镜 → format=rgba
2. 进度层 → 透明度调整 → format=rgba
3. overlay 合成（进度随时间从左到右移动）
4. [可选] 标记 GIF → 缩放 → overlay 到进度条前端
5. 缩放到目标尺寸 → yuv420p 编码
```

5. **执行 FFmpeg**：通过 `subprocess.Popen` 实时读取进度
6. **清理临时文件**：删除中间生成的 PNG 文件
7. **返回输出路径**：保存到用户配置的输出目录

---

### 2.3 Flask 路由接口

#### 2.3.1 页面与静态资源

| 路由 | 方法 | 说明 |
|------|------|------|
| `/` | GET | 渲染主页面 `index.html` |

#### 2.3.2 图片生成

| 路由 | 方法 | 说明 |
|------|------|------|
| `/generate` | POST | 生成进度条预览图片 |

**请求体**：
```json
{
    "total_duration": "00:10:00:00",
    "chapters": [
        {"time": "00:00:00:00", "title": "开场"},
        {"time": "00:01:45:00", "title": "核心观点"}
    ],
    "width": 1920,
    "height": 90,
    "font_size": 28,
    "bg_color": "#FFFFFF",
    "text_color": "#111827",
    "separator_color": "#111827",
    "separator_width": 8
}
```

**响应**：
```json
{
    "success": true,
    "image": "data:image/png;base64,...",
    "filename": "progress-bar-20250626-143052.png"
}
```

#### 2.3.3 视频生成

| 路由 | 方法 | 说明 |
|------|------|------|
| `/generate_video` | POST | 启动视频生成任务（仅进度条） |
| `/generate_video_with_video` | POST | 启动视频生成任务（合并用户视频） |
| `/video_info` | POST | 获取视频分辨率信息 |
| `/video_progress/<job_id>` | GET | 查询视频生成进度 |
| `/download_video` | GET | 下载生成的视频 |

**生成视频流程**：
1. POST `/generate_video` 或 `/generate_video_with_video` → 返回 `job_id`
2. 轮询 GET `/video_progress/<job_id>` → 获取进度和状态
3. 完成后自动打开输出目录

**视频合并模式**（`/generate_video_with_video`）：
- 请求：FormData，包含 `video` 文件和 `config` JSON
- 后端：获取视频分辨率 → 计算进度条高度（宽度/1920*90）→ 生成进度条 PNG → FFmpeg 合并

**任务状态对象**：
```python
{
    "status": "running" | "done" | "error",
    "progress": 0-100,
    "message": "错误信息（仅错误时）",
    "download_url": "/download_video（完成时）"
}
```

#### 2.3.4 配置管理

| 路由 | 方法 | 说明 |
|------|------|------|
| `/output_dir` | GET | 获取输出目录 |
| `/output_dir` | POST | 设置输出目录 |

#### 2.3.5 字体管理

| 路由 | 方法 | 说明 |
|------|------|------|
| `/font_options` | GET | 获取可用字体列表 |
| `/font` | GET | 获取当前字体设置 |
| `/font` | POST | 设置当前字体 |

#### 2.3.6 GIF 标记管理

| 路由 | 方法 | 说明 |
|------|------|------|
| `/gif_options` | GET | 获取可用 GIF 列表 |
| `/upload_gif` | POST | 上传自定义 GIF |
| `/delete_gif` | POST | 删除自定义 GIF |
| `/custom_gifs/` | GET | 访问自定义 GIF |

#### 2.3.7 健康检查

| 路由 | 方法 | 说明 |
|------|------|------|
| `/health` | GET | 检查 FFmpeg 和字体状态 |

**响应**：
```json
{
    "ok": true,
    "ffmpeg": true,
    "font": "PingFang.ttc"
}
```

---

### 2.4 app_webview.py - 桌面窗口版本

**职责**：使用 pywebview 创建本地桌面窗口，封装 Web 应用。

#### 2.4.1 端口查找

**`find_port(start=5000, limit=20) → int`**

查找可用的空闲端口，优先从 5000 开始尝试，最多尝试 20 个端口。

#### 2.4.2 JSBridge 类

桥接 Python 和 JavaScript 的接口类，允许前端调用本地系统功能：

| 方法 | 说明 |
|------|------|
| `browse_folder()` | 打开系统文件夹选择对话框 |
| `get_output_directory()` | 获取当前输出目录 |
| `set_output_directory(path)` | 设置输出目录 |
| `get_default_directory()` | 获取默认输出目录 |
| `reveal_in_finder()` | 在 Finder 中显示输出目录 |

**使用示例**（JavaScript）：
```javascript
// 调用 Python 方法
const path = await window.pywebview.api.browse_folder();
```

#### 2.4.3 启动流程

```
1. 创建 JSBridge 实例
2. 创建 Flask 线程（后台运行）
3. 等待 1.5 秒确保 Flask 启动
4. 创建 webview 窗口
5. 设置窗口引用到 JSBridge
6. 启动 webview 主循环
```

**窗口配置**：
```python
{
    "title": "视频进度条生成器",
    "width": 1280,
    "height": 800,
    "resizable": True,
    "min_size": (800, 600),
    "js_api": js_bridge
}
```

---

### 2.5 launcher.py - 浏览器版本

**职责**：启动本地 Flask 服务并自动打开浏览器。

**启动流程**：
1. 查找可用端口
2. 在独立线程中打开浏览器
3. 启动 Flask 应用

**适用场景**：在没有桌面环境或需要轻量运行时使用。

---

## 3. 前端模块说明

### 3.1 index.html - 页面结构

```
┌─────────────────────────────────────────────────────────────────────┐
│  顶部栏 (topbar)                                                     │
│  ├── 标题区: "Timeline Bar Studio" + "视频进度条生成器"               │
│  └── 元信息: FFmpeg状态 | 输出路径                                    │
├─────────────────────────────────────────────────────────────────────┤
│  工作区 (workspace) - 左右布局                                        │
│  ┌──────────────┬──────────────────────────────────────────────────┐│
│  │ 设置面板      │ 预览区 (preview-area)                             ││
│  │ (panel--    │  ┌─────────────────────┬───────────────────────┐ ││
│  │ settings)   │  │ Video.js 播放器     │ 图片预览               │ ││
│  │ (1/4宽度)   │  │ 拖动播放轴+添加章节  │ 进度条实时预览         │ ││
│  │             │  ├─────────────────────┴───────────────────────┤ ││
│  │ - 尺寸设置   │  │ 章节列表                                      │ ││
│  │ - 颜色设置   │  │ 默认: 00:00:00:00 开场                        │ ││
│  │ - 字体选择   │  └────────────────────────────────────────────┘ ││
│  │ - GIF标记   │                                                   ││
│  │ - 导入视频   │                                                   ││
│  │ - 操作按钮   │                                                   ││
│  │   • 生成图片 │                                                   ││
│  │   • 下载PNG  │                                                   ││
│  │   • 生成视频 │                                                   ││
│  │   • 仅进度条 │ (导入视频后显示)                                   ││
│  └──────────────┴──────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────────────┘
```

### 3.2 script.js - 核心功能

#### 3.2.1 状态管理

| 变量 | 类型 | 说明 |
|------|------|------|
| `chapters` | array | 当前章节列表 |
| `currentImageData` | string | 生成的图片 Data URL |
| `generatedVideo` | boolean | 视频是否已生成 |
| `previewTimer` | number | 预览防抖定时器 |
| `gifOptions` | array | 可用的 GIF 选项 |
| `videoPlayer` | object | Video.js 播放器实例 |
| `currentVideoFile` | File | 当前导入的视频文件 |
| `currentVideoName` | string | 当前导入的视频文件名（不含扩展名） |

#### 3.2.2 初始化流程

**`boot()`**
1. 绑定事件监听
2. 加载 GIF 选项
3. 加载输出目录
4. 加载字体选项
5. 恢复本地存储状态
6. 渲染章节列表
7. 检查 FFmpeg 健康状态
8. 启动定时预览更新

#### 3.2.3 章节管理

**`renderChapters()`**
- 根据 `chapters` 数组渲染章节列表
- 每个章节项包含：时间输入、标题输入、上下移动/插入/删除按钮

**`handleChapterAction(index, action)`**
- `up`: 上移章节
- `down`: 下移章节
- `insert`: 在下方插入新章节
- `remove`: 删除当前章节

#### 3.2.4 预览更新

**`schedulePreview(delay=350)`**
- 防抖机制，避免频繁请求
- 350ms 内如有新输入则重新计时

**`generateImage(isAuto)`**
- 调用 `/generate` 接口
- 更新预览图片
- 自动模式下静默失败（非自动模式显示错误）

#### 3.2.5 视频生成

**`generateVideo()`**
1. 如果有导入视频，调用 `/generate_video_with_video`
2. 否则调用 `/generate_video`
3. 启动轮询监控进度
4. 完成后调用 `reveal_in_finder()` 打开输出目录

**`generateProgressOnlyVideo()`**
- 仅生成纯进度条动画视频（不合并用户视频）
- 调用 `/generate_video` 接口

**`watchVideoProgress(jobId, startedAt)`**
- 每 500ms 查询一次进度
- 更新状态显示（百分比 + 耗时）
- 完成后自动打开文件夹

#### 3.2.6 空格键快捷键

**功能**：在非输入框区域按空格键控制视频播放/暂停

**实现**：
```javascript
document.addEventListener("keydown", (e) => {
    if (e.code === "Space" && !["INPUT", "TEXTAREA"].includes(e.target.tagName)) {
        e.preventDefault();
        if (videoPlayer) {
            if (videoPlayer.paused()) {
                videoPlayer.play();
            } else {
                videoPlayer.pause();
            }
        }
    }
});
```

#### 3.2.7 视频导入与自动填充

**`handleVideoImport(file)`**
- 验证文件类型（支持 MP4、WebM、MOV、AVI）
- 验证文件大小（最大 500MB）
- 使用 Blob URL 加载视频
- 显示视频容器，隐藏图片容器
- **自动填充**：
  - 总时长：`formatTime(duration, true)` → `HH:MM:SS:FF`
  - 宽度：`videoWidth`
  - 高度：`width / 1920 * 90`
  - 字号：`28 * (width / 1920)`（最小12）
  - 显示"仅生成进度条"按钮

#### 3.2.8 时间格式

**`formatTime(seconds, includeFrames = false)`**
- 统一输出 `HH:MM:SS` 或 `HH:MM:SS:FF` 格式
- 即使小时为0也保持两位数前导零
- 示例：`1:01:08` → `00:01:01:08`

**`parseTimeToSecondsWithFrames(timeStr, fps = 30)`**
- 支持解析带帧数的时间格式
- 4段格式：`HH:MM:SS:FF` → 秒数 + 帧数/fps

#### 3.2.9 GIF 标记预览

**`updateVideoMarkerPreview()`**
- 计算 GIF 在预览图中的位置
- 支持水平/垂直偏移调整
- 实时显示 GIF 动画效果

---

### 3.3 style.css - 样式系统

#### 3.3.1 配色方案

```css
:root {
    --ink: #151515;           /* 主文字色 */
    --muted: #6b7280;         /* 次要文字 */
    --line: #dedbd2;          /* 边框线色 */
    --paper: #fbfaf6;         /* 纸张背景 */
    --panel: #ffffff;         /* 面板背景 */
    --accent: #e4472e;        /* 强调色（红色） */
    --accent-dark: #9f2617;   /* 深强调色 */
    --green: #1f8a59;         /* 成功状态 */
    --danger: #b42318;        /* 危险/错误 */
    --shadow: 0 20px 50px rgba(34, 31, 26, 0.12);  /* 阴影 */
}
```

#### 3.3.2 布局结构

**工作区布局**（桌面端）：
```
grid-template-columns: 1fr 3fr
- 左侧：设置面板 (1/4)
- 右侧：预览区域 (3/4)
```

**预览区域**：
- 视频预览 + 图片预览 + 章节列表（垂直排列）

**响应式断点**：
- `≤1100px`: 设置面板占满，右侧预览区域占满
- `≤720px`: 单列紧凑布局

#### 3.3.3 组件样式

| 组件 | 说明 |
|------|------|
| `.primary-button` | 深色主按钮 |
| `.accent-button` | 红色强调按钮 |
| `.secondary-button` | 次要按钮 |
| `.ghost-button` | 幽灵按钮（边框） |
| `.danger-button` | 危险操作按钮 |
| `.spinner` | 加载动画 |
| `.chapter-item` | 章节条目（时间输入框宽度 184px） |
| `.video-container` | 视频播放器容器 |
| `.video-wrapper` | 视频包装容器（黑色背景） |
| `.video-controls` | 视频控制栏（时间显示 + 添加章节按钮） |
| `.video-js` | Video.js 播放器样式 |

#### 3.3.4 视频播放器样式

视频播放器使用 Video.js 库，样式定制包括：

- 播放按钮：红色圆形，居中显示
- 控制栏：播放/暂停、音量、时间、进度条、倍速、全屏
- 时间显示：等宽字体，格式 `01:45:12 / 10:00:00`
- 添加章节按钮：主按钮样式，触发当前时间点章节添加

---

## 4. 依赖关系

### 4.1 Python 依赖

```
Flask          # Web 框架
Pillow         # 图像处理
Werkzeug       # WSGI 工具（Flask 依赖）
imageio-ffmpeg # FFmpeg 封装
```

### 4.2 前端依赖

无外部前端依赖，纯原生实现（Video.js 通过 CDN 加载）。

### 4.3 系统依赖

| 依赖 | 说明 | 来源 |
|------|------|------|
| FFmpeg | 视频编码 | imageio-ffmpeg 自动安装或系统安装 |

---

## 5. 配置与运行

### 5.1 环境变量

| 变量 | 说明 | 示例 |
|------|------|------|
| `FONT_PATH` | 指定字体文件路径 | `static/fonts/SimHei.ttf` |
| `FFMPEG_PATH` | 指定 FFmpeg 路径 | `/usr/local/bin/ffmpeg` |

### 5.2 运行方式

#### 方式一：桌面窗口版本（推荐）

```bash
python app_webview.py
```

- 使用 pywebview 封装为桌面应用
- 支持系统文件夹选择对话框
- 完成后自动打开输出目录

#### 方式二：浏览器版本

```bash
python launcher.py
# 或直接
python app.py
```

- 自动打开默认浏览器
- 适合无桌面环境或轻量使用

### 5.3 构建打包

使用 PyInstaller 打包为独立应用：

```bash
pyinstaller video-progress-bar-webview.spec
```

**打包配置**（已优化）：
- `strip=True` - 去除二进制调试符号
- `upx=True` - 启用 UPX 压缩
- 包含 `bin/ffmpeg`、`bin/ffprobe`
- 包含 `templates`、`static`、`custom_gifs` 目录
- 设置 `_MEIPASS` 用于资源访问

**打包体积**：约 120MB

---

## 6. 数据流图

```
┌─────────────────────────────────────────────────────────────────┐
│                         用户界面层                                │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐              │
│  │  设置面板    │  │  章节管理    │  │  预览区域    │              │
│  │  (HTML/JS)  │  │  (HTML/JS)  │  │  (HTML/JS)  │              │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘              │
└─────────┼────────────────┼────────────────┼──────────────────────┘
          │                │                │
          │   AJAX / Fetch │                │
          ▼                ▼                ▼
┌─────────────────────────────────────────────────────────────────┐
│                        Flask API 层                             │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │  /generate → ProgressBarCreator.draw_static_bar()      │    │
│  │  /generate_video → run_video_job() → create_video()    │    │
│  │  /generate_video_with_video → 合并视频模式              │    │
│  │  /font_options → scan_system_fonts()                   │    │
│  │  /gif_options → CUSTOM_GIF_DIR/*.gif                   │    │
│  └─────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────┘
          │                │                │
          ▼                ▼                ▼
┌─────────────────────────────────────────────────────────────────┐
│                       核心处理层                                 │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐              │
│  │ PIL.Image   │  │ subprocess  │  │  文件系统    │              │
│  │ (图片渲染)   │  │ (FFmpeg)    │  │ (配置/GIF)  │              │
│  └─────────────┘  └─────────────┘  └─────────────┘              │
└─────────────────────────────────────────────────────────────────┘
```

---

## 7. 关键算法说明

### 7.1 章节位置计算

每个章节的 x 坐标 = `宽度 × (章节时间点 / 总时长)`

```
时间轴:  00:00    01:45    05:20    08:30    10:00
         │       │       │       │       │
位置:    0    width×0.175  width×0.533  width×0.85  width
```

### 7.2 文字自适应字号

为确保章节标题在有限宽度内完整显示，采用从大到小递减字号尝试：

```
for size in range(font_size, 8, -1):
    lines = wrap_title(text, font(size), max_width)
    if lines and total_height <= available_height:
        return size, lines
```

### 7.3 进度覆盖动画

使用 FFmpeg overlay 滤镜实现从左到右的进度覆盖：

```bash
# 进度条从 0 移动到全宽
x='overlay_w - overlay_w*t/TOTAL_DURATION'
```

### 7.4 标记 GIF 位置

标记 GIF 跟随进度条前端，位置计算：

```
x = min(max(0, width*t/T - size/2 + offset_x), width - size)
y = (height - size)/2 + offset_y
```

### 7.5 时间格式解析

**前端**：`HH:MM:SS:FF` 格式（4段，含帧数）
- `parseTimeToSecondsWithFrames("00:01:01:08", 30)` → `61.27` 秒

**后端**：`parse_time(value, fps=30)` 支持自动检测段数
- 3段格式：`HH:MM:SS` → 纯时间
- 4段格式：`HH:MM:SS:FF` → 时间 + 帧数/fps

---

## 8. 文件清单

| 文件路径 | 说明 | 行数 |
|----------|------|------|
| `app.py` | 核心 Flask 应用 | ~930 |
| `app_webview.py` | 桌面窗口启动器 | ~113 |
| `launcher.py` | 浏览器启动器 | ~38 |
| `templates/index.html` | 主页面模板（含 Video.js） | ~220 |
| `static/script.js` | 前端交互逻辑（含视频播放） | ~620 |
| `static/style.css` | 样式表（含视频播放器样式） | ~680 |
| `requirements.txt` | Python 依赖 | ~4 |
| `video-progress-bar-webview.spec` | PyInstaller 打包配置 | ~105 |
| `custom_gifs/` | 用户 GIF 存储目录 | - |
| `config.json` | 用户配置文件（运行时生成） | - |

---

## 9. 常见问题排查

### 9.1 FFmpeg 未找到

**症状**：生成视频时报错 "未找到 FFmpeg"

**排查步骤**：
1. 检查环境变量 `FFMPEG_PATH` 是否正确设置
2. 确认 `imageio-ffmpeg` 已正确安装
3. 检查打包后的 `bin/ffmpeg` 是否存在

### 9.2 字体显示异常

**症状**：中文显示为方块或乱码

**原因**：使用的字体不支持中文

**解决方案**：
1. 设置 `FONT_PATH` 环境变量指向支持中文的字体
2. 或在 UI 中选择系统自带的中文字体

### 9.3 章节文字被截断

**症状**：部分章节标题显示不完整

**原因**：章节宽度不足以容纳文字

**解决方案**：
1. 增加进度条高度
2. 减小字号
3. 缩短章节标题长度
4. 减少章节数量

### 9.4 视频生成超时

**症状**：长时间等待无响应

**原因**：
1. 视频时长过长
2. 分辨率过高
3. FFmpeg 性能不足

**优化建议**：
1. 降低帧率（从 30fps 降至 24fps）
2. 减小分辨率

### 9.5 视频无法播放

**症状**：导入视频后无法播放，显示加载失败

**原因**：
1. 浏览器不支持该视频格式
2. 视频文件损坏
3. 文件过大导致内存不足

**解决方案**：
1. 使用 Chrome 浏览器（兼容性最好）
2. 将视频转换为 MP4 (H.264) 格式
3. 确保视频文件小于 500MB

### 9.6 Video.js CDN 加载失败

**症状**：视频播放器显示异常或报错 "videojs is not defined"

**原因**：unpkg CDN 无法访问

**解决方案**：
1. 检查网络连接
2. 或使用本地 Video.js 副本

### 9.7 动画速度与视频不匹配

**症状**：生成的视频动画过慢或过快

**原因**：时间格式解析错误

**排查**：
1. 检查章节时间是否使用 `HH:MM:SS:FF` 格式
2. 检查 fps 设置是否正确

### 9.8 打包体积过大

**症状**：打包后的应用超过 100MB

**原因**：FFmpeg 完整包 + Python 运行时

**优化建议**：
1. 启用 `strip=True` 和 `upx=True`
2. 如不需要 H.265 编码，可使用精简版 FFmpeg

---

*文档版本：1.1.0*  
*最后更新：2025-06-29*
