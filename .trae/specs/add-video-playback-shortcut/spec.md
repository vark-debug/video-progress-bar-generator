# 视频播放空格键快捷键 Spec

## Why
用户需要在导入视频后快速播放/暂停预览，目前需要点击视频区域或按钮操作

## What Changes
- 添加空格键快捷键控制视频播放/暂停

## Impact
- Affected code: `static/script.js`

## Requirements
### Requirement: 空格键播放/暂停
当页面获得焦点时，按空格键应切换视频播放状态：
- 如果视频正在播放 → 暂停
- 如果视频已暂停 → 播放

#### Scenario: 快捷键控制
- **WHEN** 用户按下空格键且有视频已导入
- **THEN** 视频播放状态切换（播放↔暂停）