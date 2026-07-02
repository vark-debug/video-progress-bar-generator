import sys
import os
from pathlib import Path

block_cipher = None

project_root = Path.cwd()
app_name = "视频进度条生成器"
main_script = "launcher.py"

a = Analysis(
    [main_script],
    pathex=[str(project_root)],
    binaries=[],
    datas=[
        ("templates", "templates"),
        ("static", "static"),
        ("custom_gifs", "custom_gifs"),
    ],
    hiddenimports=[
        "flask",
        "werkzeug",
        "PIL",
        "PIL.Image",
        "PIL.ImageDraw",
        "PIL.ImageFont",
        "imageio_ffmpeg",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name=app_name,
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name=app_name,
)

app = BUNDLE(
    coll,
    name=f"{app_name}.app",
    info_plist={
        "CFBundleName": app_name,
        "CFBundleDisplayName": app_name,
        "CFBundleIdentifier": "com.videoprogressbar.app",
        "CFBundleVersion": "1.0.0",
        "CFBundleShortVersionString": "1.0.0",
        "CFBundlePackageType": "APPL",
        "CFBundleExecutable": app_name,
        "LSMinimumSystemVersion": "10.13",
        "NSHighResolutionCapable": True,
        "NSPrincipalClass": "NSApplication",
    },
    console=False,
    disable_windowed_traceback=False,
    entitlements_file=None,
)
