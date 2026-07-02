# Tasks

- [x] Task 1: 修复视频合并模式的进度条动画 FFmpeg 命令
  - [x] SubTask 1.1: 在 create_video 方法中修改视频合并模式的 FFmpeg 命令
  - [x] SubTask 1.2: 添加 lavfi color_source 作为进度条颜色输入
  - [x] SubTask 1.3: 添加 fps 滤镜把静态图转为帧序列
  - [x] SubTask 1.4: 添加 overlay 滤镜实现进度条动画
  - [x] SubTask 1.5: 确保进度条居中显示在视频底部
  - [x] SubTask 1.6: 添加 marker_gif 支持（如有）
  - [x] SubTask 1.7: 添加 `-t` 参数控制输出时长

- [x] Task 2: 添加导入视频自动填写帧数功能
  - [x] SubTask 2.1: 在 get_video_resolution 方法中添加获取帧率的逻辑
  - [x] SubTask 2.2: 更新 /video_info 路由返回帧率
  - [x] SubTask 2.3: 更新 script.js 视频导入逻辑自动设置帧数

# Task Dependencies
- Task 1 和 Task 2 已完成
- Task 3: 重新打包并测试