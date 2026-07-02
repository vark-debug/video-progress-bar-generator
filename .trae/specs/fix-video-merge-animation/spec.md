# 修复视频合并进度条动画 Spec

## Why
1. 当前视频合并模式只生成静态进度条（1帧），没有动画效果
2. 导入视频后帧数需要手动填写，用户体验不好

## What Changes
1. 修改 `create_video` 方法中视频合并模式的 FFmpeg 命令，添加动画逻辑
2. 导入视频时自动获取并填写帧数（优先使用视频原始帧率）

## Impact
- Affected code: 
  - `app.py` 中 `create_video` 方法的视频合并部分
  - `app.py` 中 `get_video_resolution` 方法（添加获取帧率）
  - `app.py` 中 `/video_info` 路由（返回帧率）
  - `script.js` 中视频导入逻辑（自动设置帧数）

## ADDED Requirements

### Requirement: 视频合并进度条动画
系统 SHALL 在合并用户视频时生成带动画效果的进度条。

#### Scenario: 视频合并模式
- **WHEN** 用户导入视频后点击生成视频
- **THEN** 生成包含进度条动画的视频，进度条居中显示在视频底部，动画持续 total_duration 秒

### Requirement: 导入视频自动填写帧数
系统 SHALL 在用户导入视频后自动获取并填写帧数。

#### Scenario: 导入视频
- **WHEN** 用户导入视频文件
- **THEN** 自动获取视频帧率并填入帧数输入框

## Technical Details

### 1. 原版动画逻辑分析
```
输入0: 静态进度条图片 (-loop 1 -i input.png)
输入1: lavfi color_source（进度条颜色）
滤镜链:
  [0:v]fps={fps} → 把静态图转为帧序列
  [1:v] → 进度条颜色视频
  overlay:x='-overlay_w+overlay_w*t/{duration}' → 颜色位置随时间从右到左移动
```

### 2. 新实现逻辑（视频合并模式）
```
输入0: 用户视频
输入1: 静态进度条图片 (-loop 1)
输入2: lavfi color_source（进度条颜色）
滤镜链:
  [0:v]format=yuv420p → 用户视频
  [1:v]fps={fps} → 进度条图片转帧序列
  [2:v] → 进度条颜色
  [1:v][2:v]overlay:x='-overlay_w+overlay_w*t/{duration}' → 颜色叠加在进度条上产生动画
  [result]scale={width}:{height} → 缩放到目标尺寸
  [0:v][result]overlay:x=(W-w)/2:y=(H-h) → 叠加在视频底部
```

### 3. 获取视频帧率
在 `get_video_resolution` 方法中添加获取帧率的逻辑：
```
ffprobe -v error -select_streams v:0 -show_entries stream=r_frame_rate -of default=noprint_wrappers=1:nokey=1
返回格式: "30/1" → 转换为 30 fps
```

### 4. FFmpeg 命令结构（视频合并模式）
```bash
ffmpeg -y
  -i user_video.mp4                    # 输入0: 用户视频
  -loop 1 -i progress_bar.png          # 输入1: 进度条图片
  -f lavfi -i "color=c=#RRGGBB:s=WxH:r=FPS:d=Duration"  # 输入2: 进度条颜色
  -filter_complex "
    [1:v]fps={fps},format=rgba[bar_base];
    [bar_base][2:v]overlay=x='-overlay_w+overlay_w*t/{duration}':y=0:eval=frame[bar_animated];
    [bar_animated]scale={width}:{height}[bar];
    [0:v][bar]overlay=x=(W-w)/2:y=(H-h):shortest=1[out]
  "
  -map [out] -t {duration}
  -c:v libx264 -preset veryfast -crf 18 output.mp4
```