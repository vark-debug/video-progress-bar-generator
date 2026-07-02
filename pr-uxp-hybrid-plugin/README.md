# Premiere Pro UXP 混合插件 - 视频进度条生成器

## 项目概述

### 项目背景

本项目旨在将现有的"视频进度条生成器"独立应用移植为 Adobe Premiere Pro UXP 混合插件，通过结合 UXP 前端技术和 C++ 原生库实现完全集成化的视频进度条生成功能。

### 现有项目分析

**当前技术栈：**
- 后端：Python Flask
- 图像处理：Pillow (PIL)
- 视频生成：FFmpeg 子进程调用
- 前端：HTML/CSS/JavaScript Web UI
- 打包：PyInstaller

**核心功能：**
1. 生成带章节标记的静态进度条图像
2. 生成动态进度条动画视频
3. 支持自定义样式（颜色、字体、大小等）
4. 支持 GIF 标记物（进度指示器）
5. 支持叠加到用户视频

### 为什么选择 UXP 混合插件？

**Premiere Pro UXP API 能力分析：**

| 功能 | UXP 原生支持 | ExtendScript 支持 | 混合插件支持 |
|------|-------------|-------------------|-------------|
| 项目/序列操作 | ✅ 完全支持 | ✅ 完全支持 | ✅ 完全支持 |
| 轨道/剪辑管理 | ✅ 完全支持 | ✅ 完全支持 | ✅ 完全支持 |
| 素材导入 | ✅ 完全支持 | ✅ 完全支持 | ✅ 完全支持 |
| 文本创建 | ❌ 不支持 | ✅ 完全支持 | ✅ 完全支持 |
| 关键帧动画 | ❌ 不支持 | ✅ 完全支持 | ✅ 完全支持 |
| 图像渲染 | ❌ 不支持 | ❌ 不支持 | ✅ 完全支持 |
| 视频编解码 | ❌ 不支持 | ❌ 不支持 | ✅ 完全支持 |

**结论：** UXP 混合插件是唯一能够实现完整功能的方案。

### 项目目标

1. **功能完整性**：保留现有应用的所有功能
2. **无缝集成**：直接在 Premiere Pro 内使用
3. **性能优化**：通过 C++ 原生库实现高性能
4. **用户体验**：现代化 UI，流畅的操作流程

### 最低系统要求

| 组件 | 最低版本 |
|------|---------|
| **Premiere Pro** | 26.2+ (2025 v26) |
| **UXP Developer Tool** | 2.2+ |
| **Creative Cloud Desktop** | 5.10+ |
| **操作系统** | macOS 12+ / Windows 10+ |
| **Xcode** (macOS) | 14.0+ |
| **Visual Studio** (Windows) | 2019+ |
| **CMake** | 3.20+ |

### 技术选型

| 层级 | 技术选择 | 说明 |
|------|---------|------|
| **UI 层** | UXP (HTML/CSS/JS) + Spectrum Widgets | Adobe 官方 UI 框架 |
| **逻辑层** | JavaScript (ES6+) | 业务逻辑和 Premiere API 调用 |
| **原生处理层** | C++17 + FFmpeg | 图像渲染和视频生成 |
| **图像库** | Skia | 高性能 2D 图形渲染 |
| **视频处理** | FFmpeg (libav*) | 视频编解码和合成 |

### 相关资源

- [Premiere Pro UXP 官方文档](https://developer.adobe.com/premiere-pro/uxp/)
- [Premiere Pro API 参考](https://developer.adobe.com/premiere-pro/uxp/ppro-reference/)
- [UXP 混合插件文档](https://developer.adobe.com/premiere-pro/uxp/plugins/hybrid-plugins/)
- [UXP 混合插件 SDK](https://developer.adobe.com/console) (需从 Adobe Developer Console 下载)

---

## 文档目录

1. [系统架构文档](./docs/architecture.md)
2. [C++ 原生库设计文档](./docs/cpp-library-design.md)
3. [UXP UI 设计文档](./docs/ui-design.md)
4. [API 接口规范文档](./docs/api-specification.md)
5. [开发任务清单](./docs/tasks.md)
6. [编译和打包指南](./docs/build-guide.md)

---

## 版本历史

| 版本 | 日期 | 作者 | 说明 |
|------|------|------|------|
| 1.0.0 | 2026-06-30 | - | 初始版本，方案设计 |