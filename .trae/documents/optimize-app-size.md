# 应用打包体积优化计划

## 摘要
优化视频进度条生成器的PyInstaller打包配置，通过启用strip和UPX压缩减少打包体积。

## 当前状态分析

### 体积分布（120MB）
- Python运行时：~45-50MB
- FFmpeg及库文件：~50-60MB
- PIL图像库：~10-15MB
- 其他：~10-15MB

### 问题
- `strip=False` - 未去除调试符号
- `upx=False` - 未启用UPX压缩
- 未排除不需要的模块

## 优化方案（基础优化）

### 1. 修改spec文件
**文件**: `video-progress-bar-webview.spec`

**修改内容**:
1. 启用`strip=True`去除二进制调试符号
2. 启用`upx=True`压缩可执行文件和库
3. 添加`upx_exclude`排除与UPX不兼容的库

### 2. 具体代码变更

```python
# EXE和COLLECT中启用strip和upx
exe = EXE(
    pyz, a.scripts, [],
    exclude_binaries=True,
    name=app_name,
    strip=True,      # 新增：去除调试符号
    upx=True,        # 新增：启用UPX压缩
    console=False,
)

coll = COLLECT(
    exe, a.binaries, a.zipfiles, a.datas,
    strip=True,      # 新增
    upx=True,        # 新增
    upx_exclude=[    # 新增：排除可能出问题的库
        'libx264*',
        'libx265*',
    ],
    name=app_name,
)
```

## 实施步骤

1. 读取当前spec文件
2. 修改EXE和COLLECT配置，添加strip和upx参数
3. 重新打包
4. 对比打包前后的体积

## 预期效果

- 预期减少体积：40-60MB
- 目标体积：60-80MB
- 风险等级：低（标准优化操作）

## 验证方法

1. 打包完成后检查dist目录大小
2. 启动应用验证功能正常
3. 生成视频测试核心功能