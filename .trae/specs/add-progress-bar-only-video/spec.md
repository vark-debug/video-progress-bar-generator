# 仅生成进度条视频 Spec

## Why
当用户导入视频后，可能只需要生成进度条视频（不带原视频画面），而不是将进度条叠加到原视频上

## What Changes
- 在"生成视频"按钮下方添加"仅生成进度条"按钮
- 点击后生成纯进度条动画视频

## Impact
- Affected code: `templates/index.html`, `static/script.js`

## Requirements
### Requirement: 仅生成进度条视频按钮
当有视频导入时，显示"仅生成进度条"按钮

#### Scenario: 生成纯进度条视频
- **WHEN** 用户导入视频并点击"仅生成进度条"按钮
- **THEN** 生成不带原视频画面的纯进度条动画视频