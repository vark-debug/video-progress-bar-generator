# 修复视频合并音频和精确帧率 Spec

## Why
1. 当前视频合并模式生成的视频没有声音，用户视频的音频丢失了
2. 当前生成的视频时长精确到秒，但正常视频需要精确到帧

## What Changes
1. 保留用户视频的音频轨道
2. 确保视频时长精确到帧（不是秒）

## Impact
- Affected code: `app.py` 中 `create_video` 方法的视频合并部分的 FFmpeg 命令

## Technical Analysis

### 问题 1：音频丢失
当前 FFmpeg 命令只使用了 `-map "[out]"`，只映射了视频流。需要同时映射音频流：
```bash
# 当前命令（只有视频）
-map "[out]"

# 需要改为（保留音频）
-map "0:a?"     # 映射用户视频的音频流（如果有）
-map "[out]"    # 映射处理后的视频流
```

### 问题 2：精确到帧
当前使用了 `-fps_mode cfr` 但可能不够精确。需要：
1. 确保 `-r` 参数正确设置帧率
2. 检查 `-t` 参数是否正确限制时长
3. 可能需要使用更精确的帧级别时间控制

### FFmpeg 命令修改
```bash
ffmpeg -y
  -i user_video.mp4                    # 输入0: 用户视频
  -loop 1 -i progress_bar.png          # 输入1: 进度条图片
  -f lavfi -i "color=c=#RRGGBB:..."   # 输入2: 进度条颜色
  -filter_complex "..."
  -map 0:a?                            # 映射原视频音频（如果有）
  -map "[out]"                         # 映射处理后视频
  -t {duration}
  -r {fps}
  -c:v libx264 -preset veryfast -crf 18
  -c:a aac -b:a 192k                   # 保留音频编码
  -shortest                            # 取视频或音频较短者
  output.mp4
```