# 视频进度条生成器

一个用于生成视频章节进度条图片和进度条动画视频的本地 Web 工具。

> **注意**：本项目的 **macOS 版本**是由 [样样松s](https://github.com/yangyangsong) 基于原版 Windows 版本修改而来。原版 Windows 版本由样样松s编写。

## 运行

```bash
pip install -r requirements.txt
python app.py
```

打开：

```text
http://127.0.0.1:5000
```

## 字体

程序会按这个顺序读取字体：

1. 环境变量 `FONT_PATH`
2. `static/` 目录下的第一个 `.ttf/.otf/.ttc`
3. `static/fonts/` 目录下的第一个 `.ttf/.otf/.ttc`
4. Pillow 默认字体

所以字体文件可以直接放在 `static` 目录下，也可以放在 `static/fonts` 目录下。

如果要指定字体：

```bash
FONT_PATH=static/MyFont.ttf python app.py
```

Windows PowerShell：

```powershell
$env:FONT_PATH="static/MyFont.ttf"
python app.py
```

页面右上角会显示当前读取到的字体文件名。

## FFmpeg

默认优先使用当前 Python 环境中 `imageio-ffmpeg` 提供的 FFmpeg，不需要单独在系统里安装 FFmpeg。

如果要指定 FFmpeg：

```bash
FFMPEG_PATH=/path/to/ffmpeg python app.py
```

## 时间格式

- `255`：255 秒
- `4:15`：4 分 15 秒
- `1:04:15`：1 小时 4 分 15 秒

## GIF ????

????????????? GIF ????????

- ???
- ???
- ??
- ???

????????? GIF ??????????????????????? GIF ?????

```text
static/gifs/
```

??????????????????? `spark.gif`?`pulse.gif` ? `arrow.gif`?
