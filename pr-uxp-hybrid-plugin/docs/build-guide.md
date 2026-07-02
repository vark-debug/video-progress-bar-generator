# 编译打包指南

## 1. 开发环境准备

### 1.1 概述

本指南详细说明如何编译和打包 Premiere Pro UXP 混合插件。编译过程涉及三个主要部分：C++ 原生库的编译、UXP 插件的构建以及最终的打包分发。整个编译流程在本地开发机器上完成，打包产物可以在不同平台上测试和分发。

在开始编译之前，请确保已阅读并理解了系统架构文档和 C++ 原生库设计文档。本指南假设开发者具备基本的命令行操作能力和 C++ 开发经验。

### 1.2 硬件要求

编译环境对硬件有一定要求，特别是 C++ 原生库的编译会消耗较多资源。

| 组件 | 最低要求 | 推荐配置 |
|------|---------|---------|
| 处理器 | 4 核心 | 8 核心或以上 |
| 内存 | 8 GB | 16 GB 或以上 |
| 磁盘空间 | 20 GB 可用 | 50 GB 或以上 SSD |
| 操作系统 | macOS 12+ 或 Windows 10+ | 最新稳定版 |

磁盘空间主要用于存储第三方库的编译产物和中间文件。FFmpeg 和 Skia 的完整编译产物可能占用数 GB 的空间。如果磁盘空间有限，可以在编译完成后删除不需要的中间文件。

### 1.3 软件依赖

#### 通用依赖

以下软件是所有平台都需要安装的基础依赖：

**CMake 3.20+** 是本项目的构建系统，用于管理编译过程、生成平台特定的构建文件以及处理依赖关系。可以从 CMake 官方网站下载安装包，或者使用包管理器安装。在 macOS 上可以通过 Homebrew 安装：`brew install cmake`。在 Windows 上可以使用 Chocolatey：`choco install cmake`。安装完成后，确保 CMake 的 bin 目录已添加到系统 PATH 环境变量中。

**Git** 用于版本控制和获取源代码。如果系统中尚未安装 Git，需要先完成安装。在 macOS 上通常已经预装，如果没有可以通过 Homebrew 安装。在 Windows 上可以从 Git 官网下载安装包。安装时建议选择"Use Git from the Windows Command Prompt"选项，并将默认分支名设置为 main。

**Python 3.8+** 用于运行部分构建脚本和配置工具。大多数 macOS 系统已预装 Python，可以通过终端输入 `python3 --version` 验证。在 Windows 上需要从 Python 官网下载安装包，安装时勾选"Add Python to PATH"选项。

#### macOS 依赖

在 macOS 上开发需要安装以下软件：

**Xcode 14.0+** 是 macOS 平台的核心开发工具，提供编译器、调试器和各种开发工具。可以从 Mac App Store 免费下载安装。安装完成后，打开 Xcode 并接受许可协议。然后安装 Xcode Command Line Tools，这可以通过在终端运行 `xcode-select --install` 完成。Command Line Tools 提供了 GCC、Clang 编译器以及 make 等构建工具。

**Homebrew** 是 macOS 上最流行的包管理器，用于安装各种开发工具和库。虽然大多数依赖可以手动安装，但使用 Homebrew 可以简化安装过程并自动处理依赖关系。可以从 Homebrew 官网获取安装命令。安装完成后，使用 `brew doctor` 检查安装状态。

#### Windows 依赖

在 Windows 上开发需要安装以下软件：

**Visual Studio 2019+** 是 Windows 平台的主要开发环境。本项目使用 MSVC 编译器，需要安装包含 C++ 工作负载的 Visual Studio。从 Visual Studio 官网下载安装程序，运行后选择"使用 C++ 的桌面开发"工作负载。安装选项中确保包含 Windows 10/11 SDK 和 MSVC v142 构建工具。

**Visual Studio Code** 是推荐的代码编辑器，虽然不是必需的，但可以提高开发效率。从 VS Code 官网下载安装包，安装时建议勾选"添加到 PATH"和"注册为受支持的文件类型的编辑器"选项。安装完成后，安装 C++ 扩展和 CMake Tools 扩展以获得更好的开发体验。

**Windows SDK** 随 Visual Studio 一起安装，但如果需要单独安装或更新，可以在 Microsoft 官网下载。确保安装的 SDK 版本与项目的目标 Windows 版本兼容。

### 1.4 目录结构

建议按照以下结构组织工作目录：

```
~/development/
├── premiere-pro-plugins/
│   └── progress-bar-generator/
│       ├── src/
│       │   ├── plugin/          # UXP 插件源码
│       │   └── native/          # C++ 原生库源码
│       ├── deps/                # 第三方依赖
│       │   ├── skia/
│       │   └── ffmpeg/
│       ├── build/               # 构建输出目录
│       │   ├── macOS/
│       │   └── windows/
│       ├── test/                # 测试文件
│       └── docs/                # 文档
└── adobe-uxp-developer-tool/    # UXP Developer Tool
```

这个目录结构将所有相关项目组织在一起，便于管理。deps 目录用于存放第三方依赖的源码和编译产物，build 目录用于存放各平台的构建输出。

## 2. 获取和构建第三方依赖

### 2.1 FFmpeg 库准备

FFmpeg 是视频处理的核心依赖。本项目需要 FFmpeg 的开发包，包括头文件和编译好的库文件。

#### macOS 上的 FFmpeg 准备

在 macOS 上，推荐使用 Homebrew 安装 FFmpeg 开发包：

```bash
# 安装 FFmpeg 及开发依赖
brew install ffmpeg

# 验证安装
ffmpeg -version
```

Homebrew 安装的 FFmpeg 默认不包含开发头文件。如果需要从源码编译原生库，可能需要安装额外的依赖或从 FFmpeg 官网下载源码自行编译。对于初步开发，使用 Homebrew 版本已经足够。

如果需要获取 FFmpeg 的头文件和库文件用于 C++ 编译，可以设置以下环境变量：

```bash
# 设置 FFmpeg 路径
export FFMPEG_ROOT=$(brew --prefix)/Cellar/ffmpeg/<版本号>
export PKG_CONFIG_PATH="$FFMPEG_ROOT/lib/pkgconfig:$PKG_CONFIG_PATH"
export LD_LIBRARY_PATH="$FFMPEG_ROOT/lib:$LD_LIBRARY_PATH"
```

#### Windows 上的 FFmpeg 准备

在 Windows 上，推荐使用 vcpkg 或从 zeranoe 获取预编译包：

**使用 vcpkg 安装（推荐）：**

```powershell
# 克隆 vcpkg 仓库
git clone https://github.com/Microsoft/vcpkg.git
cd vcpkg

# 运行安装脚本
.\bootstrap-vcpkg.bat

# 安装 FFmpeg 及相关库
.\vcpkg install ffmpeg[x264,x265] --triplets x64-windows
```

安装完成后，设置环境变量指向 vcpkg 安装目录：

```powershell
# 设置环境变量（需要管理员权限）
setx VCPKG_ROOT "C:\path\to\vcpkg"
setx VCPKG_DEFAULT_TRIPLET "x64-windows"
```

**使用预编译包：**

如果不想使用 vcpkg，可以从 FFmpeg 官网下载 Zeranoe 构建版本。选择 shared 开发包下载，解压到本地目录，然后配置相应的环境变量。

#### FFmpeg 库组件需求

本项目需要以下 FFmpeg 库组件：

| 库名称 | 用途 | 必需 |
|--------|------|------|
| libavformat | 媒体容器处理 | 是 |
| libavcodec | 音视频编解码 | 是 |
| libavutil | 工具函数 | 是 |
| libavfilter | 音视频滤镜 | 是 |
| libswscale | 图像缩放 | 是 |
| libswresample | 音频重采样 | 否 |

### 2.2 Skia 库准备

Skia 是 2D 图形渲染的核心依赖。由于 Skia 的编译过程较为复杂，建议使用预编译版本或通过 Skia 的官方工具链编译。

#### 获取 Skia 预编译库

对于快速开始，可以使用 Google 提供的 Skia 预编译版本。从 Skia releases 页面下载对应平台的预编译包。下载后解压到 deps/skia 目录。

#### 从源码编译 Skia

如果需要特定配置或最新版本，可以从源码编译 Skia：

**macOS 编译步骤：**

```bash
# 克隆 Skia 仓库
git clone https://skia.googlesource.com/skia.git
cd skia

# 使用 Skia 工具下载依赖
python tools/git-sync-deps

# 创建构建目录
mkdir -p out/Release

# 使用 GN 生成构建文件
cat > out/Release/args.gn << 'EOF'
is_official_build = true
is_debug = false
target_os = "mac"
target_cpu = "x64"
skia_use_metal = true
skia_use_gl = false
EOF

# 生成 Xcode 项目
python tools/git-sync-deps
gn gen out/Release --args-file=out/Release/args.gn

# 编译
ninja -C out/Release skia
```

**Windows 编译步骤：**

```powershell
# 克隆 Skia 仓库
git clone https://skia.googlesource.com/skia.git
cd skia

# 下载依赖
python tools/git-sync-deps

# 创建构建目录
mkdir out\Release

# 生成 Ninja 构建文件
$env:path += ";C:\path\to\depot_tools"
gn gen out\Release --args="is_official_build=true is_debug=false target_os=`"win`" target_cpu=`"x64`""

# 编译
ninja -C out/Release skia
```

编译 Skia 需要 Depot Tools，这是 Google 内部的构建工具集合。如果下载遇到困难，可以参考 Skia 官方文档获取更多帮助。

### 2.3 UXP Hybrid Plugin SDK 准备

UXP Hybrid Plugin SDK 是连接 JavaScript 和 C++ 的桥梁，需要从 Adobe Developer Console 下载。

#### 下载 SDK

1. 访问 Adobe Developer Console：https://developer.adobe.com/console/
2. 登录 Adobe 账户
3. 创建新项目或选择已有项目
4. 在项目中添加"Premiere Pro"产品
5. 下载 UXP Hybrid Plugin SDK

如果下载页面显示"Access Denied"，需要按照 Adobe 的说明配置 Creative Cloud 开发者权限。具体步骤请参考 Adobe 官方文档。

#### SDK 内容说明

下载的 SDK 压缩包包含以下内容：

```
uxp-hybrid-plugin-sdk/
├── README.md                    # 快速开始指南
├── src/
│   ├── api/
│   │   ├── UxpAddonTypes.h      # 类型定义
│   │   └── UxpAddonShared.h     # 核心 API
│   ├── utilities/
│   │   └── UxpAddon.h           # 工具宏
│   └── template/                # 示例模板
│       ├── template-dev/        # 开发模板
│       └── template-plugin/     # 插件模板
└── docs/                       # API 文档
```

将 SDK 解压到项目的 deps 目录下，保持目录结构不变。

## 3. C++ 原生库编译

### 3.1 项目配置

C++ 原生库使用 CMake 作为构建系统。项目根目录下的 CMakeLists.txt 是主要的配置文件。

#### CMakeLists.txt 结构

```cmake
cmake_minimum_required(VERSION 3.20)
project(ProgressBarProcessor VERSION 1.0.0 LANGUAGES CXX)

# 设置 C++ 标准
set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

# 输出目录配置
set(CMAKE_LIBRARY_OUTPUT_DIRECTORY ${CMAKE_BINARY_DIR}/lib)
set(CMAKE_ARCHIVE_OUTPUT_DIRECTORY ${CMAKE_BINARY_DIR}/lib)
set(CMAKE_RUNTIME_OUTPUT_DIRECTORY ${CMAKE_BINARY_DIR}/bin)

# 依赖路径配置
set(DEPENDENCIES_DIR ${CMAKE_SOURCE_DIR}/../deps)
set(SKIA_ROOT ${DEPENDENCIES_DIR}/skia)
set(FFMPEG_ROOT ${DEPENDENCIES_DIR}/ffmpeg)

# 查找依赖
find_package(Skia REQUIRED)
find_package(FFmpeg REQUIRED COMPONENTS avformat avcodec avutil avfilter swscale)

# 添加子目录
add_subdirectory(src)
```

#### 平台特定配置

```cmake
# src/CMakeLists.txt

# 根据平台添加不同的编译选项
if(APPLE)
    set(CMAKE_OSX_DEPLOYMENT_TARGET "12.0")
    set(CMAKE_OSX_ARCHITECTURES "arm64;x86_64")
    
    # 添加 Metal 框架
    find_library(METAL_FRAMEWORK Metal)
    find_library(METAL_LIBRARIES MetalKit)
    
    list(APPEND PLATFORM_LIBS ${METAL_FRAMEWORK} ${METAL_LIBRARIES})
elseif(WIN32)
    # 添加 Windows 特定定义
    add_definitions(-D_CRT_SECURE_NO_WARNINGS)
    add_definitions(-DWIN32_LEAN_AND_MEAN)
    
    # 添加库搜索路径
    link_directories(${FFMPEG_ROOT}/lib)
endif()

# 创建共享库
add_library(progress_processor SHARED
    addon_main.cpp
    progress_processor.cpp
    skia_renderer.cpp
    ffmpeg_processor.cpp
)

# 链接依赖
target_link_libraries(progress_processor
    PRIVATE
    ${SKIA_LIBRARIES}
    ${FFMPEG_LIBRARIES}
    ${PLATFORM_LIBS}
)

# 设置输出名称为 uxpaddon 格式
set_target_properties(progress_processor PROPERTIES
    OUTPUT_NAME "progress_processor.uxpaddon"
    PREFIX ""
)
```

### 3.2 编译步骤

#### macOS 编译

在 macOS 上编译 C++ 原生库：

```bash
# 进入项目根目录
cd ~/development/premiere-pro-plugins/progress-bar-generator

# 创建构建目录
mkdir -p build/macOS
cd build/macOS

# 配置 CMake（指定依赖路径）
cmake ../../src/native \
    -DCMAKE_BUILD_TYPE=Release \
    -DDEPENDENCIES_DIR=../../deps \
    -DSKIA_ROOT=../../deps/skia \
    -DFFMPEG_ROOT=/usr/local

# 编译
cmake --build . --config Release --parallel

# 检查输出
ls -la lib/
```

编译成功后，会在 `build/macOS/lib/` 目录下生成 `progress_processor.uxpaddon` 文件。

#### Windows 编译

在 Windows 上编译 C++ 原生库：

```powershell
# 进入项目根目录
cd C:\development\premiere-pro-plugins\progress-bar-generator

# 创建构建目录
mkdir build\windows
cd build\windows

# 使用 Visual Studio 开发者命令提示符运行
cmake ..\src\native ^
    -G "Visual Studio 17 2022" ^
    -A x64 ^
    -DCMAKE_BUILD_TYPE=Release ^
    -DDEPENDENCIES_DIR=..\..\deps ^
    -DSKIA_ROOT=..\..\deps\skia ^
    -DFFMPEG_ROOT=%VCPKG_ROOT%\installed\x64-windows

# 编译
cmake --build . --config Release --parallel

# 检查输出
dir lib\
```

编译成功后，会在 `build\windows\lib\` 目录下生成 `progress_processor.uxpaddon` 文件。

### 3.3 编译问题排查

#### 常见编译错误

**找不到 FFmpeg 库：**

```
Could not find FFmpeg (missing: FFMPEG_LIBRARY)
```

解决方案：确保 FFMPEG_ROOT 环境变量指向包含 FFmpeg 库文件的目录。检查目录结构是否正确，lib 目录下应包含 .a 或 .lib 文件。

**Skia 头文件找不到：**

```
fatal error: 'skia/core/SkTypes.h' file not found
```

解决方案：检查 SKIA_ROOT 环境变量是否正确设置。确保 Skia 的 include 目录结构与代码中的引用匹配。

**链接错误 - 未定义的符号：**

```
Undefined symbols for architecture x86_64: "_avcodec_open2"
```

解决方案：确保所有需要的 FFmpeg 组件都已链接。检查 CMakeLists.txt 中的 find_package 和 target_link_libraries 语句。

#### 调试编译问题

如果遇到编译问题，可以启用详细的编译输出：

```bash
# macOS/Linux
cmake ../../src/native -DCMAKE_VERBOSE_MAKEFILE=ON

# Windows
cmake ..\src\native -DCMAKE_VERBOSE_MAKEFILE=ON
```

详细输出会显示每个编译命令的完整参数，便于定位问题。

## 4. UXP 插件构建

### 4.1 插件结构

UXP 插件的标准结构如下：

```
src/plugin/
├── manifest.json          # 插件清单
├── index.html             # 入口 HTML
├── index.js               # 入口 JavaScript
├── styles/
│   └── main.css           # 主样式表
├── components/            # UI 组件
│   └── ...
├── services/              # 服务层
│   └── ...
├── utils/                 # 工具函数
│   └── ...
└── resources/             # 资源文件
    ├── images/
    └── locales/
```

### 4.2 manifest.json 配置

插件清单文件定义插件的基本信息和运行时配置：

```json
{
    "id": "com.progressbar.generator",
    "name": "视频进度条生成器",
    "version": "1.0.0",
    "main": "index.html",
    "manifestVersion": 5,
    "entrypoints": [
        {
            "type": "panel",
            "id": "progressbar.main",
            "label": {
                "default": "进度条生成器",
                "zh_CN": "进度条生成器"
            },
            "minimumSize": {
                "width": 400,
                "height": 600
            },
            "maximumSize": {
                "width": 1200,
                "height": 1600
            }
        }
    ],
    "dependencies": {
        "premierepro": "^26.0.0"
    },
    "host": {
        "app": "premierepro",
        "minVersion": "26.2.0"
    },
    "requiredPermissions": {
        "nativeDialogs": true,
        "fileSystem": ["read", "write", "user"]
    }
}
```

### 4.3 本地开发和调试

使用 UXP Developer Tool 进行本地开发和调试：

```bash
# 进入插件目录
cd ~/development/premiere-pro-plugins/progress-bar-generator/src/plugin

# 启动 UXP Developer Tool
uxp devtool
```

在 UXP Developer Tool 界面中：

1. 点击"Add Plugin"添加插件
2. 选择插件目录
3. 点击插件卡片上的"Load Unpacked"加载插件
4. 在 Premiere Pro 中打开插件面板
5. 打开开发者工具进行调试

加载原生模块需要将编译好的 .uxpaddon 文件放到插件的正确位置。通常放在插件目录的 lib 子目录下：

```
src/plugin/
├── lib/
│   ├── macOS/
│   │   └── progress_processor.uxpaddon
│   └── windows/
│       └── progress_processor.uxpaddon
├── manifest.json
└── ...
```

在 JavaScript 中加载原生模块：

```javascript
// 根据平台选择正确的模块
const platform = navigator.platform.toLowerCase();
const libPath = platform.includes('mac') 
    ? './lib/macOS/progress_processor.uxpaddon'
    : './lib/windows/progress_processor.uxpaddon';

const processor = require(libPath);
```

## 5. 打包与分发

### 5.1 打包准备

在打包之前，确保完成以下检查：

**版本号检查**：确认 manifest.json 中的版本号正确。建议使用语义化版本号格式（主版本.次版本.修订号）。

**资源完整性检查**：确认所有资源文件（图片、字体、本地化文件）都已包含在项目中。

**原生模块检查**：确认 macOS 和 Windows 两个平台的 .uxpaddon 文件都已编译完成。

**测试完成检查**：确认所有功能测试都已通过，没有已知问题。

### 5.2 打包脚本

创建自动化打包脚本简化打包流程：

#### macOS 打包脚本

```bash
#!/bin/bash
# scripts/package-macos.sh

set -e

PLUGIN_NAME="progress-bar-generator"
VERSION=$(grep '"version"' src/plugin/manifest.json | sed 's/.*"version": "\([^"]*\)".*/\1/')
OUTPUT_DIR="package/macOS"

echo "正在打包 $PLUGIN_NAME v$VERSION (macOS)..."

# 清理旧包
rm -rf $OUTPUT_DIR
mkdir -p $OUTPUT_DIR

# 复制插件文件
cp -r src/plugin/* $OUTPUT_DIR/

# 复制原生模块
mkdir -p $OUTPUT_DIR/lib/macOS
cp build/macOS/lib/progress_processor.uxpaddon $OUTPUT_DIR/lib/macOS/

# 创建 ZIP 包
cd $OUTPUT_DIR
zip -r ../../dist/${PLUGIN_NAME}-${VERSION}-macOS.zip .
cd ../..

echo "打包完成: dist/${PLUGIN_NAME}-${VERSION}-macOS.zip"
```

#### Windows 打包脚本

```powershell
# scripts/package-windows.ps1

$PluginName = "progress-bar-generator"
$Version = (Get-Content "src\plugin\manifest.json" | Select-String '"version"' -AllMatches | ForEach-Object { $_.Matches.Value -replace '.*"version":\s*"([^"]*)".*', '$1' })
$OutputDir = "package\windows"

Write-Host "正在打包 $PluginName v$Version (Windows)..."

# 清理旧包
if (Test-Path $OutputDir) { Remove-Item -Recurse -Force $OutputDir }
New-Item -ItemType Directory -Path $OutputDir | Out-Null

# 复制插件文件
Copy-Item -Path "src\plugin\*" -Destination $OutputDir -Recurse

# 复制原生模块
New-Item -ItemType Directory -Path "$OutputDir\lib\windows" | Out-Null
Copy-Item -Path "build\windows\lib\progress_processor.uxpaddon" -Destination "$OutputDir\lib\windows\"

# 创建 ZIP 包
Compress-Archive -Path "$OutputDir\*" -DestinationPath "dist\${PluginName}-${Version}-windows.zip"

Write-Host "打包完成: dist\${PluginName}-${Version}-windows.zip"
```

### 5.3 创建 UXP 包

UXP 插件最终以 .uxp 文件形式分发。可以使用 UXP Developer Tool 创建包：

1. 在 UXP Developer Tool 中选择插件
2. 点击"Package"按钮
3. 选择输出路径
4. 等待打包完成

或者使用命令行工具：

```bash
# 安装 uxp 工具
npm install -g @adobe/uxp-tools

# 创建包
uxp package src/plugin -o dist/plugin.uxp
```

### 5.4 代码签名

为插件添加签名可以提高安全性和用户信任度。

**插件签名**使用 Adobe 提供的证书签名工具。在 Adobe Developer Console 中创建项目后，可以获取签名证书。使用 uxp 工具签名：

```bash
# 使用证书签名插件
uxp sign dist/plugin.uxp \
    --certificate /path/to/certificate.p12 \
    --password <证书密码>
```

**原生模块签名**在 macOS 上需要签名以允许加载。使用 codesign 工具：

```bash
# macOS 签名
codesign -s "Developer ID Application: Your Name" \
    build/macOS/lib/progress_processor.uxpaddon
```

### 5.5 分发

#### Adobe Exchange 分发

最正式的分发渠道是通过 Adobe Exchange。提交插件到 Exchange 需要：

1. 在 Adobe Exchange Developer Console 中注册为合作伙伴
2. 创建插件列表
3. 提交审核
4. 通过审核后发布

#### 直接下载分发

对于内部使用或测试，可以直接提供 ZIP 或 UXP 文件下载。创建下载页面，包含安装说明和系统要求。

## 6. 持续集成配置

### 6.1 GitHub Actions 配置

创建 `.github/workflows/build.yml` 配置自动化构建：

```yaml
name: Build and Package

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]
  release:
    types: [published]

jobs:
  build-macos:
    runs-on: macos-latest
    
    steps:
      - uses: actions/checkout@v4
      
      - name: Install dependencies
        run: |
          brew install cmake ffmpeg
          
      - name: Build C++ library
        run: |
          mkdir -p build/macOS
          cd build/macOS
          cmake ../../src/native -DCMAKE_BUILD_TYPE=Release
          cmake --build . --config Release --parallel
          
      - name: Package plugin
        run: |
          chmod +x scripts/package-macos.sh
          ./scripts/package-macos.sh
          
      - name: Upload artifacts
        uses: actions/upload-artifact@v4
        with:
          name: macOS-package
          path: dist/*.zip

  build-windows:
    runs-on: windows-latest
    
    steps:
      - uses: actions/checkout@v4
      
      - name: Install dependencies
        run: |
          choco install cmake ninja vcpkg -y
          vcpkg integrate install
          
      - name: Build C++ library
        shell: pwsh
        run: |
          mkdir build\windows
          cd build\windows
          cmake ..\src\native -G "Visual Studio 17 2022" -A x64 -DCMAKE_BUILD_TYPE=Release
          cmake --build . --config Release --parallel
          
      - name: Package plugin
        shell: pwsh
        run: |
          .\scripts\package-windows.ps1
          
      - name: Upload artifacts
        uses: actions/upload-artifact@v4
        with:
          name: windows-package
          path: dist/*.zip
```

### 6.2 版本管理

使用 GitHub Actions 自动管理版本号和发布：

```yaml
# 在 release workflow 中
- name: Create GitHub Release
  if: github.event_name == 'release'
  uses: actions/create-release@v1
  env:
    GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
  with:
    tag_name: ${{ github.event.release.tag_name }}
    release_name: ${{ github.event.release.tag_name }}
    draft: false
    prerelease: ${{ contains(github.event.release.tag_name, 'beta') }}
```

## 7. 相关文档

- [系统架构文档](./architecture.md)
- [C++ 原生库设计文档](./cpp-library-design.md)
- [UXP UI 设计文档](./ui-design.md)
- [API 接口规范文档](./api-specification.md)
- [开发任务清单](./tasks.md)