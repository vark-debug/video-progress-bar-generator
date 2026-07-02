# Tasks

- [x] Task 1: 修复音频丢失问题
  - [x] SubTask 1.1: 在 FFmpeg 命令中添加 `-map 0:a?` 保留原视频音频
  - [x] SubTask 1.2: 添加音频编码参数 `-c:a aac -b:a 192k`

- [x] Task 2: 修复精确帧率问题
  - [x] SubTask 2.1: 检查 `-r` 参数位置是否正确
  - [x] SubTask 2.2: 确保 `-fps_mode cfr` 正确工作

# Task Dependencies
- Task 1 和 Task 2 已完成
- Task 3: 重新打包并测试