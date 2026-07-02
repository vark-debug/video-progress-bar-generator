from __future__ import annotations

import base64
import io
import json
import os
import shutil
import subprocess
import sys
import threading
import uuid
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from urllib.parse import quote

from flask import Flask, jsonify, render_template, request, send_file, send_from_directory
from PIL import Image, ImageDraw, ImageFont

APP_DIR = Path(__file__).resolve().parent
BUNDLE_DIR = Path(getattr(sys, "_MEIPASS", APP_DIR))
RUNTIME_DIR = Path(sys.executable).resolve().parent if getattr(sys, "frozen", False) else APP_DIR
EXTERNAL_STATIC_DIR = RUNTIME_DIR / "static"
EXTERNAL_TEMPLATE_DIR = RUNTIME_DIR / "templates"
RESOURCE_DIR = RUNTIME_DIR if EXTERNAL_STATIC_DIR.exists() and EXTERNAL_TEMPLATE_DIR.exists() else BUNDLE_DIR
STATIC_DIR = RESOURCE_DIR / "static"
FONT_EXTENSIONS = (".ttf", ".otf", ".ttc")


def get_user_data_dir() -> Path:
    if getattr(sys, "frozen", False):
        base = Path.home() / "Library" / "Application Support"
    else:
        base = APP_DIR
    return base / "视频进度条生成器"


USER_DATA_DIR = get_user_data_dir()
USER_DATA_DIR.mkdir(parents=True, exist_ok=True)
CUSTOM_GIF_DIR = USER_DATA_DIR / "custom_gifs"
CUSTOM_GIF_DIR.mkdir(parents=True, exist_ok=True)

CONFIG_FILE = USER_DATA_DIR / "config.json"


def get_default_output_dir() -> Path:
    return Path.home() / "Documents" / "视频进度条生成器"


def load_config() -> dict:
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def save_config(config: dict) -> None:
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(config, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


def get_output_dir() -> Path:
    config = load_config()
    output_path = config.get("output_dir", "")
    if output_path:
        path = Path(output_path)
        if path.exists() and path.is_dir():
            return path
    return get_default_output_dir()


def set_output_dir(path: str) -> bool:
    target = Path(path)
    if not target.exists():
        try:
            target.mkdir(parents=True, exist_ok=True)
        except Exception:
            return False
    if not target.is_dir():
        return False
    config = load_config()
    config["output_dir"] = str(target)
    save_config(config)
    return True


def get_font_setting() -> dict:
    config = load_config()
    return {
        "font_path": config.get("font_path", ""),
        "font_name": config.get("font_name", "默认"),
    }


def set_font_setting(font_path: str, font_name: str) -> bool:
    if font_path and not Path(font_path).exists():
        return False
    config = load_config()
    config["font_path"] = font_path
    config["font_name"] = font_name
    save_config(config)
    return True


def scan_system_fonts() -> list[dict]:
    fonts = []
    seen_names = set()

    font_dirs = []
    if sys.platform == "darwin":
        font_dirs.extend([
            Path("/System/Library/Fonts"),
            Path("/Library/Fonts"),
            Path.home() / "Library" / "Fonts",
        ])
    elif sys.platform == "win32":
        font_dirs.append(Path(os.environ.get("WINDIR", r"C:\Windows")) / "Fonts")

    for font_dir in font_dirs:
        if not font_dir.exists():
            continue
        for ext in FONT_EXTENSIONS:
            for font_file in font_dir.glob(f"*{ext}"):
                try:
                    font_name = font_file.stem.replace(".ttc", "")
                    for suffix in [" Regular", " Bold", " Light", " Medium", " Italic", " Thin"]:
                        font_name = font_name.replace(suffix, "")
                    if font_name in seen_names:
                        continue
                    seen_names.add(font_name)
                    fonts.append({
                        "name": font_name,
                        "path": str(font_file),
                        "source": "system"
                    })
                except Exception:
                    continue

    fonts.sort(key=lambda x: x["name"].lower())
    return fonts


OUTPUT_DIR = get_output_dir()
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

app = Flask(__name__, template_folder=str(RESOURCE_DIR / "templates"), static_folder=str(STATIC_DIR))

PINGFANG_FONTS = [
    "PingFang SC",
    "PingFang TC",
    "PingFang HK",
    "SF Pro Display",
    "SF Pro Text",
]

RISKY_FONTS = ["PingFang", "SF Pro", "Heiti", "Songti", "STXihei", "STHeiti", "Hiragino Sans GB"]


def is_risky_font(font_name: str) -> bool:
    return any(risky in font_name for risky in RISKY_FONTS)


@dataclass(frozen=True)
class Chapter:
    time: float
    title: str


class ProgressBarCreator:
    def __init__(self, custom_font_path: str = None) -> None:
        if custom_font_path and Path(custom_font_path).exists():
            self.font_path = Path(custom_font_path)
        else:
            self.font_path = self.find_font_path()

    def find_font_path(self) -> Path | None:
        if sys.platform == "darwin":
            search_dirs = [
                Path("/System/Library/Fonts"),
                Path("/Library/Fonts"),
                Path.home() / "Library" / "Fonts",
            ]
            for directory in search_dirs:
                if not directory.exists():
                    continue
                for extension in FONT_EXTENSIONS:
                    fonts = sorted(directory.glob(f"*{extension}"))
                    if fonts:
                        for font in fonts:
                            name = font.stem.replace(".ttc", "")
                            for suffix in [" Regular", " Bold", " Light", " Medium", " Italic", " Thin", " Semibold", " Ultralight"]:
                                name = name.replace(suffix, "")
                            if name in PINGFANG_FONTS:
                                return font
                        for font in fonts:
                            name = font.name.lower()
                            if any(k in name for k in ["pingfang", "heiti", "songti", "yahei", "msyh"]):
                                return font
                        return fonts[0]

        configured = os.environ.get("FONT_PATH", "").strip()
        if configured:
            configured_path = Path(configured)
            if not configured_path.is_absolute():
                configured_path = APP_DIR / configured_path
            if configured_path.exists() and configured_path.suffix.lower() in FONT_EXTENSIONS:
                return configured_path

        search_dirs = [STATIC_DIR, STATIC_DIR / "fonts"]
        if sys.platform == "win32":
            search_dirs.append(Path(os.environ.get("WINDIR", r"C:\Windows")) / "Fonts")

        for directory in search_dirs:
            if not directory.exists():
                continue
            for extension in FONT_EXTENSIONS:
                fonts = sorted(directory.glob(f"*{extension}"))
                if fonts:
                    for font in fonts:
                        name = font.name.lower()
                        if sys.platform == "win32" and any(k in name for k in ["msyh", "yahei", "simhei", "simsun"]):
                            return font
                    return fonts[0]

        return None

    def parse_time(self, value: str | int | float, fps: int = 30) -> float:
        if isinstance(value, (int, float)):
            return float(value)

        raw = str(value).strip()
        if not raw:
            raise ValueError("时间不能为空")

        try:
            parts = [float(part) for part in raw.split(":")]
        except ValueError as exc:
            raise ValueError(f"无法解析时间：{value}") from exc

        if len(parts) == 1:
            return parts[0]
        if len(parts) == 2:
            minutes, seconds = parts
            return minutes * 60 + seconds
        if len(parts) == 3:
            hours, minutes, seconds = parts
            return hours * 3600 + minutes * 60 + seconds
        if len(parts) >= 4:
            hours, minutes, seconds, frames = parts[0], parts[1], parts[2], parts[3]
            return hours * 3600 + minutes * 60 + seconds + frames / fps
        raise ValueError(f"时间格式不正确：{value}")

    def format_time(self, seconds: float) -> str:
        seconds_int = max(0, int(round(seconds)))
        hours = seconds_int // 3600
        minutes = (seconds_int % 3600) // 60
        secs = seconds_int % 60
        if hours:
            return f"{hours}:{minutes:02d}:{secs:02d}"
        return f"{minutes}:{secs:02d}"

    def normalize_chapters(self, total_duration: float, chapters: list[dict], fps: int = 30) -> list[Chapter]:
        normalized: list[Chapter] = []
        for chapter in chapters:
            title = str(chapter.get("title", "")).strip()
            if not title:
                continue
            time_point = self.parse_time(chapter.get("time", "0"), fps=fps)
            if time_point < 0 or time_point > total_duration:
                raise ValueError(f"章节「{title}」的时间超出总时长")
            normalized.append(Chapter(time_point, title))

        if not normalized:
            raise ValueError("请至少添加一个章节")

        normalized.sort(key=lambda item: item.time)
        if normalized[0].time != 0:
            normalized.insert(0, Chapter(0, normalized[0].title))
        return normalized

    def load_font(self, size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
        size = max(8, min(int(size), 96))
        if self.font_path:
            return ImageFont.truetype(str(self.font_path), size)
        return ImageFont.load_default()

    def wrap_title(
        self,
        draw: ImageDraw.ImageDraw,
        text: str,
        font: ImageFont.ImageFont,
        max_width: int,
        max_lines: int = 3,
    ) -> list[str]:
        if max_width <= 12:
            return []

        lines: list[str] = []
        for paragraph in text.splitlines() or [text]:
            current = ""
            for char in paragraph:
                candidate = current + char
                box = draw.textbbox((0, 0), candidate, font=font)
                if box[2] - box[0] <= max_width or not current:
                    current = candidate
                else:
                    lines.append(current)
                    current = char
                if len(lines) >= max_lines:
                    break
            if current and len(lines) < max_lines:
                lines.append(current)
            if len(lines) >= max_lines:
                break

        if not lines:
            return []

        if len(lines) == max_lines:
            while lines[-1] and draw.textbbox((0, 0), lines[-1] + "...", font=font)[2] > max_width:
                lines[-1] = lines[-1][:-1]
            lines[-1] = lines[-1] + "..." if lines[-1] else "..."
        return lines

    def draw_static_bar(
        self,
        total_duration: str | int | float,
        chapters: list[dict],
        width: int,
        height: int,
        bg_color: str,
        text_color: str,
        separator_color: str,
        separator_width: int,
        font_size: int,
        fps: int = 30,
    ) -> Image.Image:
        if isinstance(total_duration, str):
            total_seconds = self.parse_time(total_duration, fps=fps)
        else:
            total_seconds = float(total_duration)
        if total_seconds <= 0:
            raise ValueError("总时长必须大于 0")

        width = max(320, min(int(width), 7680))
        height = max(36, min(int(height), 720))
        separator_width = max(1, min(int(separator_width), 40))
        chapters_data = self.normalize_chapters(total_seconds, chapters, fps=fps)

        transparent = str(bg_color).lower() == "transparent"
        image = Image.new("RGBA", (width, height), (255, 255, 255, 0) if transparent else bg_color)
        draw = ImageDraw.Draw(image)
        font = self.load_font(font_size)

        positions = [int(width * chapter.time / total_seconds) for chapter in chapters_data]
        if positions[0] != 0:
            positions.insert(0, 0)
        positions.append(width)

        padding_y = max(4, height // 12)
        for x in sorted(set(positions[1:-1])):
            draw.line((x, padding_y, x, height - padding_y), fill=separator_color, width=separator_width)

        for index, chapter in enumerate(chapters_data):
            section_start = positions[index]
            section_end = positions[index + 1] if index + 1 < len(positions) else width
            section_width = max(0, section_end - section_start)
            if section_width < 16:
                continue

            usable_width = max(8, section_width - 16)
            current_size = int(font_size)
            lines: list[str] = []
            current_font = font

            while current_size >= 8:
                current_font = self.load_font(current_size)
                lines = self.wrap_title(draw, chapter.title, current_font, usable_width)
                if lines:
                    line_heights = [
                        draw.textbbox((0, 0), line, font=current_font)[3]
                        - draw.textbbox((0, 0), line, font=current_font)[1]
                        for line in lines
                    ]
                    if sum(line_heights) + (len(lines) - 1) * 4 <= height - 10:
                        break
                current_size -= 1

            if not lines:
                continue

            metrics = [draw.textbbox((0, 0), line, font=current_font) for line in lines]
            line_height = max(box[3] - box[1] for box in metrics)
            total_text_height = line_height * len(lines) + 4 * (len(lines) - 1)
            y = (height - total_text_height) // 2

            for line, box in zip(lines, metrics):
                line_width = box[2] - box[0]
                x = section_start + (section_width - line_width) // 2
                draw.text((x, y), line, fill=text_color, font=current_font)
                y += line_height + 4

        return image

    def image_to_data_url(self, image: Image.Image) -> str:
        buffer = io.BytesIO()
        image.save(buffer, "PNG", optimize=True)
        encoded = base64.b64encode(buffer.getvalue()).decode("ascii")
        return f"data:image/png;base64,{encoded}"

    def find_ffmpeg(self) -> str | None:
        configured = os.environ.get("FFMPEG_PATH")
        if configured and Path(configured).exists():
            return configured

        try:
            import imageio_ffmpeg
            imageio_ffmpeg_path = imageio_ffmpeg.get_ffmpeg_exe()
            if imageio_ffmpeg_path and Path(imageio_ffmpeg_path).exists():
                return str(imageio_ffmpeg_path)
        except Exception:
            pass

        search_dirs = []
        if getattr(sys, "frozen", False):
            meipass = Path(getattr(sys, "_MEIPASS", ""))
            if meipass.exists():
                search_dirs.append(meipass)
            search_dirs.append(BUNDLE_DIR)
            search_dirs.append(RUNTIME_DIR)
            contents_dir = RUNTIME_DIR.parent
            if contents_dir.exists():
                search_dirs.append(contents_dir / "Frameworks")
                search_dirs.append(contents_dir / "Resources")

        for search_dir in search_dirs:
            if not search_dir.exists():
                continue
            for pattern in ["**/ffmpeg", "**/ffmpeg-*", "**/imageio_ffmpeg/binaries/ffmpeg*"]:
                for candidate in search_dir.glob(pattern):
                    if candidate.is_file() and os.access(str(candidate), os.X_OK):
                        return str(candidate)

        system_ffmpeg = shutil.which("ffmpeg")
        if system_ffmpeg:
            return system_ffmpeg

        bundled_candidates = []
        if sys.platform == "win32":
            bundled_candidates.extend([
                BUNDLE_DIR / "bin" / "ffmpeg.exe",
                RUNTIME_DIR / "bin" / "ffmpeg.exe",
            ])
        else:
            bundled_candidates.extend([
                BUNDLE_DIR / "bin" / "ffmpeg",
                RUNTIME_DIR / "bin" / "ffmpeg",
            ])
        for candidate in bundled_candidates:
            if candidate.exists() and os.access(str(candidate), os.X_OK):
                return str(candidate)

        return None

    def resolve_marker_gif(self, marker: str | None) -> Path | None:
        marker_key = str(marker or "none").strip()
        if not marker_key or marker_key == "none":
            return None

        if marker_key.startswith("custom:"):
            try:
                filename = safe_gif_filename(marker_key.split(":", 1)[1])
            except ValueError:
                return None
            path = CUSTOM_GIF_DIR / filename
            if path.exists() and path.suffix.lower() == ".gif":
                return path
            return None

        return None

    def get_video_resolution(self, video_path: str) -> tuple[int, int]:
        """使用 ffprobe 获取视频分辨率"""
        probe_path = None

        if not probe_path:
            try:
                import imageio_ffmpeg
                img_ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
                if img_ffmpeg:
                    img_bin = Path(img_ffmpeg).parent
                    for name in ["ffprobe", "ffprobe.exe"]:
                        candidate = img_bin / name
                        if candidate.exists():
                            probe_path = str(candidate)
                            break
            except Exception:
                pass

        if not probe_path:
            for search_dir in [BUNDLE_DIR, RUNTIME_DIR]:
                for pattern in ["**/ffprobe", "**/ffprobe-*", "**/imageio_ffmpeg/binaries/ffprobe*"]:
                    for candidate in search_dir.glob(pattern):
                        if candidate.is_file() and os.access(str(candidate), os.X_OK):
                            probe_path = str(candidate)
                            break
                    if probe_path:
                        break
                if probe_path:
                    break

        if not probe_path:
            result = subprocess.run(["which", "ffprobe"], capture_output=True, text=True)
            if result.returncode == 0:
                probe_path = result.stdout.strip()

        if not probe_path:
            return 1920, 1080

        try:
            result = subprocess.run(
                [
                    probe_path,
                    "-v", "error",
                    "-select_streams", "v:0",
                    "-show_entries", "stream=width,height",
                    "-of", "csv=s=x:p=0",
                    str(video_path)
                ],
                capture_output=True,
                text=True,
                timeout=10
            )

            if result.stdout:
                parts = result.stdout.strip().split("x")
                if len(parts) == 2:
                    try:
                        return int(parts[0]), int(parts[1])
                    except ValueError:
                        pass
        except Exception:
            pass

        return 1920, 1080

    def get_video_info(self, video_path: str) -> dict:
        """使用 ffprobe 获取视频信息（分辨率和帧率）"""
        probe_path = None

        if not probe_path:
            try:
                import imageio_ffmpeg
                img_ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
                if img_ffmpeg:
                    img_bin = Path(img_ffmpeg).parent
                    for name in ["ffprobe", "ffprobe.exe"]:
                        candidate = img_bin / name
                        if candidate.exists():
                            probe_path = str(candidate)
                            break
            except Exception:
                pass

        if not probe_path:
            for search_dir in [BUNDLE_DIR, RUNTIME_DIR]:
                for pattern in ["**/ffprobe", "**/ffprobe-*", "**/imageio_ffmpeg/binaries/ffprobe*"]:
                    for candidate in search_dir.glob(pattern):
                        if candidate.is_file() and os.access(str(candidate), os.X_OK):
                            probe_path = str(candidate)
                            break
                    if probe_path:
                        break
                if probe_path:
                    break

        if not probe_path:
            result = subprocess.run(["which", "ffprobe"], capture_output=True, text=True)
            if result.returncode == 0:
                probe_path = result.stdout.strip()

        result_info = {"width": 1920, "height": 1080, "fps": 30}

        if not probe_path:
            return result_info

        try:
            result = subprocess.run(
                [
                    probe_path,
                    "-v", "error",
                    "-select_streams", "v:0",
                    "-show_entries", "stream=width,height,r_frame_rate",
                    "-of", "default=noprint_wrappers=1:nokey=1",
                    str(video_path)
                ],
                capture_output=True,
                text=True,
                timeout=10
            )

            if result.stdout:
                lines = result.stdout.strip().split("\n")
                if len(lines) >= 2:
                    try:
                        parts = lines[0].split("x")
                        if len(parts) == 2:
                            result_info["width"] = int(parts[0])
                            result_info["height"] = int(parts[1])
                    except ValueError:
                        pass

                if len(lines) >= 3:
                    try:
                        fps_str = lines[2].strip()
                        if "/" in fps_str:
                            num, den = fps_str.split("/")
                            result_info["fps"] = round(int(num) / int(den))
                        else:
                            result_info["fps"] = int(fps_str)
                    except (ValueError, ZeroDivisionError):
                        pass
        except Exception:
            pass

        return result_info


    def create_video(self, data: dict, chapters: list[dict], progress_callback=None, user_video_path: str = None) -> Path:
        ffmpeg = self.find_ffmpeg()
        if not ffmpeg:
            raise RuntimeError("未找到 FFmpeg。请设置 FFMPEG_PATH，或确认 bin 目录中已放入 ffmpeg。")

        fps = max(1, min(int(data.get("fps", 30)), 60))
        total_duration = self.parse_time(data.get("total_duration", "0"), fps=fps)
        if total_duration <= 0:
            raise ValueError("总时长必须大于 0")

        job_id = uuid.uuid4().hex
        current_output_dir = get_output_dir()
        current_output_dir.mkdir(parents=True, exist_ok=True)
        input_png = current_output_dir / f"{job_id}.png"
        
        video_name = data.get("video_name", "")
        if video_name:
            safe_name = Path(video_name).name.strip() or "video"
            output_mp4 = current_output_dir / f"{safe_name}_进度条.mp4"
        else:
            output_mp4 = current_output_dir / f"{job_id}.mp4"

        has_user_video = user_video_path and Path(user_video_path).exists()

        if has_user_video:
            video_width, video_height = self.get_video_resolution(user_video_path)
            progress_height = round(video_width / 1920 * 90)
            progress_width = video_width
            progress_color = clean_hex(data.get("progress_color", "#111827"))
            progress_opacity = max(0, min(float(data.get("progress_opacity", 30)), 100)) / 100
            marker_gif = self.resolve_marker_gif(data.get("marker_gif", "none"))
            marker_size = max(16, min(int(data.get("marker_size", max(28, progress_height // 2))), progress_height * 2))
            marker_offset_x = max(-progress_width, min(int(data.get("marker_offset_x", 0)), progress_width))
            marker_offset_y = max(-progress_height * 2, min(int(data.get("marker_offset_y", 0)), progress_height * 2))
            render_scale = 2
            work_width = progress_width * render_scale
            work_height = progress_height * render_scale

            image = self.draw_static_bar(
                total_duration=total_duration,
                chapters=chapters,
                width=work_width,
                height=work_height,
                bg_color=data.get("bg_color", "#FFFFFF"),
                text_color=data.get("text_color", "#111827"),
                separator_color=data.get("separator_color", "#111827"),
                separator_width=int(data.get("separator_width", 8)) * render_scale,
                font_size=int(data.get("font_size", 24)) * render_scale,
                fps=fps,
            )
            image.convert("RGB").save(input_png, "PNG", optimize=True)

            color_source = (
                f"color=c={progress_color}:"
                f"s={work_width}x{work_height}:r={fps}:d={total_duration:.3f}"
            )
            progress_x = f"-overlay_w+overlay_w*t/{total_duration:.6f}"

            command = [
                ffmpeg, "-y", "-hide_banner", "-loglevel", "error",
                "-i", str(user_video_path),
                "-loop", "1", "-i", str(input_png),
                "-f", "lavfi", "-i", color_source,
            ]

            if marker_gif:
                command.extend(["-stream_loop", "-1", "-ignore_loop", "0", "-i", str(marker_gif)])
                scaled_marker_size = marker_size * render_scale if marker_size else progress_height
                marker_x = (
                    f"min(max(0,main_w*t/{total_duration:.6f}-overlay_w/2+({marker_offset_x})),"
                    f"main_w-overlay_w)"
                )
                marker_y = f"(main_h-overlay_h)/2+({marker_offset_y})"
                filter_complex = [
                    f"[1:v]fps={fps},format=rgba,settb=AVTB,setpts=N/{fps}/TB[bar_base]",
                    f"[2:v]format=rgba,colorchannelmixer=aa={progress_opacity:.3f},settb=AVTB,setpts=N/{fps}/TB[progress]",
                    f"[bar_base][progress]overlay=x='{progress_x}':y=0:eval=frame:shortest=1[bar_anim]",
                    f"[3:v]fps={fps},scale={scaled_marker_size}:-1:flags=lanczos,format=rgba,settb=AVTB,setpts=N/{fps}/TB[marker]",
                    f"[bar_anim][marker]overlay=x='{marker_x}':y='{marker_y}':eval=frame:shortest=1[bar_marked]",
                    f"[bar_marked]scale={progress_width}:{progress_height}:flags=lanczos[bar]",
                    f"[0:v][bar]overlay=x=(W-w)/2:y=(H-h):shortest=1[out]",
                ]
            else:
                filter_complex = [
                    f"[1:v]fps={fps},format=rgba,settb=AVTB,setpts=N/{fps}/TB[bar_base]",
                    f"[2:v]format=rgba,colorchannelmixer=aa={progress_opacity:.3f},settb=AVTB,setpts=N/{fps}/TB[progress]",
                    f"[bar_base][progress]overlay=x='{progress_x}':y=0:eval=frame:shortest=1[bar_anim]",
                    f"[bar_anim]scale={progress_width}:{progress_height}:flags=lanczos[bar]",
                    f"[0:v][bar]overlay=x=(W-w)/2:y=(H-h):shortest=1[out]",
                ]

            command.extend([
                "-filter_complex", ";".join(filter_complex),
                "-map", "0:a?",
                "-map", "[out]",
                "-t", f"{total_duration:.3f}",
                "-r", str(fps),
                "-c:v", "libx264", "-preset", "veryfast", "-crf", "18",
                "-c:a", "aac", "-b:a", "192k",
                "-movflags", "+faststart",
                "-progress", "pipe:1", "-nostats",
                str(output_mp4),
            ])

            try:
                process = subprocess.Popen(
                    command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                    text=True, encoding="utf-8", errors="replace"
                )
                ffmpeg_log: list[str] = []
                if process.stdout:
                    for raw_line in process.stdout:
                        line = raw_line.strip()
                        if not line:
                            continue
                        if line.startswith("out_time_ms="):
                            try:
                                seconds = int(line.split("=", 1)[1]) / 1_000_000
                            except ValueError:
                                continue
                            percent = round(max(0, min(seconds / total_duration * 100, 99.99)), 2)
                            if progress_callback:
                                progress_callback(percent)
                        elif line == "progress=end":
                            if progress_callback:
                                progress_callback(100)
                        elif "=" not in line:
                            ffmpeg_log.append(line)
                            ffmpeg_log = ffmpeg_log[-30:]

                return_code = process.wait()
                if return_code != 0:
                    message = "\n".join(ffmpeg_log).strip() or "FFmpeg 生成失败"
                    raise RuntimeError(message)
                if progress_callback:
                    progress_callback(100)
            finally:
                input_png.unlink(missing_ok=True)
            return output_mp4

        width = int(data.get("width", 1920))
        height = int(data.get("height", 90))
        fps = max(1, min(int(data.get("fps", 30)), 60))
        progress_color = clean_hex(data.get("progress_color", "#111827"))
        progress_opacity = max(0, min(float(data.get("progress_opacity", 30)), 100)) / 100
        marker_gif = self.resolve_marker_gif(data.get("marker_gif", "none"))
        marker_size = max(16, min(int(data.get("marker_size", max(28, height // 2))), height * 2))
        marker_offset_x = max(-width, min(int(data.get("marker_offset_x", 0)), width))
        marker_offset_y = max(-height * 2, min(int(data.get("marker_offset_y", 0)), height * 2))
        render_scale = 2
        work_width = width * render_scale
        work_height = height * render_scale

        image = self.draw_static_bar(
            total_duration=total_duration,
            chapters=chapters,
            width=work_width,
            height=work_height,
            bg_color=data.get("bg_color", "#FFFFFF"),
            text_color=data.get("text_color", "#111827"),
            separator_color=data.get("separator_color", "#111827"),
            separator_width=int(data.get("separator_width", 8)) * render_scale,
            font_size=int(data.get("font_size", 24)) * render_scale,
            fps=fps,
        )

        job_id = uuid.uuid4().hex
        current_output_dir = get_output_dir()
        current_output_dir.mkdir(parents=True, exist_ok=True)
        input_png = current_output_dir / f"{job_id}.png"
        
        video_name = data.get("video_name", "")
        if video_name:
            safe_name = Path(video_name).name.strip() or "video"
            output_mp4 = current_output_dir / f"{safe_name}_进度条.mp4"
        else:
            output_mp4 = current_output_dir / f"{job_id}.mp4"
            
        image.convert("RGB").save(input_png, "PNG", optimize=True)

        color_source = (
            f"color=c={progress_color}:"
            f"s={work_width}x{work_height}:r={fps}:d={total_duration:.3f}"
        )
        progress_x = f"-overlay_w+overlay_w*t/{total_duration:.6f}"
        filter_complex = [
            f"[0:v]fps={fps},format=rgba,settb=AVTB,setpts=N/{fps}/TB[base]",
            f"[1:v]format=rgba,colorchannelmixer=aa={progress_opacity:.3f},settb=AVTB,setpts=N/{fps}/TB[progress]",
            f"[base][progress]overlay=x='{progress_x}':y=0:eval=frame:shortest=1[bar]",
        ]
        command = [
            ffmpeg,
            "-y",
            "-hide_banner",
            "-loglevel",
            "error",
            "-loop",
            "1",
            "-i",
            str(input_png),
            "-f",
            "lavfi",
            "-i",
            color_source,
        ]

        if marker_gif:
            command.extend(["-stream_loop", "-1", "-ignore_loop", "0", "-i", str(marker_gif)])
            scaled_marker_size = marker_size * render_scale
            offset_x = marker_offset_x * render_scale
            offset_y = marker_offset_y * render_scale
            marker_x = (
                f"min(max(0,main_w*t/{total_duration:.6f}-overlay_w/2+({offset_x})),"
                f"main_w-overlay_w)"
            )
            marker_y = f"(main_h-overlay_h)/2+({offset_y})"
            filter_complex.extend(
                [
                    f"[2:v]fps={fps},scale={scaled_marker_size}:-1:flags=lanczos,format=rgba,settb=AVTB,setpts=N/{fps}/TB[marker]",
                    f"[bar][marker]overlay=x='{marker_x}':y='{marker_y}':eval=frame:shortest=1[marked]",
                    f"[marked]scale={width}:{height}:flags=lanczos,format=yuv420p[v]",
                ]
            )
        else:
            filter_complex.append(f"[bar]scale={width}:{height}:flags=lanczos,format=yuv420p[v]")

        command.extend(
            [
                "-t",
                f"{total_duration:.3f}",
                "-filter_complex",
                ";".join(filter_complex),
                "-map",
                "[v]",
                "-r",
                str(fps),
                "-fps_mode",
                "cfr",
                "-c:v",
                "libx264",
                "-preset",
                "veryfast",
                "-crf",
                "18",
                "-movflags",
                "+faststart",
                "-progress",
                "pipe:1",
                "-nostats",
                str(output_mp4),
            ]
        )

        try:
            process = subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                errors="replace",
            )
            ffmpeg_log: list[str] = []
            if process.stdout:
                for raw_line in process.stdout:
                    line = raw_line.strip()
                    if not line:
                        continue
                    if line.startswith("out_time_ms="):
                        try:
                            seconds = int(line.split("=", 1)[1]) / 1_000_000
                        except ValueError:
                            continue
                        percent = round(max(0, min(seconds / total_duration * 100, 99.99)), 2)
                        if progress_callback:
                            progress_callback(percent)
                    elif line == "progress=end":
                        if progress_callback:
                            progress_callback(100)
                    elif "=" not in line:
                        ffmpeg_log.append(line)
                        ffmpeg_log = ffmpeg_log[-30:]

            return_code = process.wait()
            if return_code != 0:
                message = "\n".join(ffmpeg_log).strip() or "FFmpeg \u751f\u6210\u5931\u8d25"
                raise RuntimeError(message)
            if progress_callback:
                progress_callback(100)
        finally:
            input_png.unlink(missing_ok=True)

        return output_mp4


def safe_gif_filename(filename: str) -> str:
    name = Path(str(filename or "")).name.strip().replace("\\", "_").replace("/", "_")
    for char in '<>:"|?*':
        name = name.replace(char, "_")
    name = name.strip(" .")
    if not name.lower().endswith(".gif"):
        raise ValueError("\u8bf7\u4e0a\u4f20 .gif \u6587\u4ef6")
    if not name or name.lower() == ".gif":
        raise ValueError("GIF \u6587\u4ef6\u540d\u4e0d\u80fd\u4e3a\u7a7a")
    if len(name) > 120:
        stem = Path(name).stem[:90]
        name = f"{stem}.gif"
    return name

def custom_gif_url(filename: str) -> str:
    return f"/custom_gifs/{quote(filename)}"

def clean_hex(value: str) -> str:
    value = str(value or "").strip()
    if value.startswith("#") and len(value) == 7:
        return value
    return "#111827"


def payload_from_request() -> tuple[dict, list[dict]]:
    data = request.get_json(silent=True) or {}
    chapters = data.get("chapters", [])
    if not isinstance(chapters, list):
        raise ValueError("章节数据格式不正确")
    return data, chapters


def create_creator_with_font(custom_font_path: str = None) -> ProgressBarCreator:
    font_setting = get_font_setting()
    effective_font = custom_font_path or font_setting.get("font_path", "")
    if effective_font and Path(effective_font).exists():
        return ProgressBarCreator(effective_font)
    return ProgressBarCreator()


creator = ProgressBarCreator()
generated_video_path: Path | None = None
VIDEO_JOBS: dict[str, dict] = {}
VIDEO_JOBS_LOCK = threading.Lock()


def update_video_job(job_id: str, **changes) -> None:
    with VIDEO_JOBS_LOCK:
        job = VIDEO_JOBS.get(job_id)
        if job is not None:
            job.update(changes)


def run_video_job(job_id: str, data: dict, chapters: list[dict], user_video_path: str = None) -> None:
    global generated_video_path
    temp_video_path = None

    try:
        def report(percent: float) -> None:
            update_video_job(job_id, progress=round(max(0, min(percent, 100)), 2))

        bar_creator = create_creator_with_font()

        if user_video_path and Path(user_video_path).exists():
            temp_video_path = user_video_path
            path = bar_creator.create_video(data, chapters, progress_callback=report, user_video_path=temp_video_path)
        else:
            path = bar_creator.create_video(data, chapters, progress_callback=report)

        generated_video_path = path
        update_video_job(job_id, status="done", progress=100, download_url="/download_video")
    except Exception as exc:
        update_video_job(job_id, status="error", message=str(exc), progress=0)



@app.route("/")
def index():
    return render_template("index.html")


@app.route("/generate", methods=["POST"])
def generate_progress_bar():
    try:
        data, chapters = payload_from_request()
        bar_creator = create_creator_with_font()
        fps = max(1, min(int(data.get("fps", 30)), 60))
        image = bar_creator.draw_static_bar(
            total_duration=data.get("total_duration", "10:00"),
            chapters=chapters,
            width=int(data.get("width", 1920)),
            height=int(data.get("height", 90)),
            bg_color=data.get("bg_color", "#FFFFFF"),
            text_color=data.get("text_color", "#111827"),
            separator_color=data.get("separator_color", "#111827"),
            separator_width=int(data.get("separator_width", 8)),
            font_size=int(data.get("font_size", 24)),
            fps=fps,
        )
        return jsonify(
            {
                "success": True,
                "image": bar_creator.image_to_data_url(image),
                "filename": f"progress-bar-{datetime.now():%Y%m%d-%H%M%S}.png",
            }
        )
    except Exception as exc:
        return jsonify({"success": False, "message": str(exc)}), 400


@app.route("/generate_video", methods=["POST"])
def generate_video():
    try:
        data, chapters = payload_from_request()
    except Exception as exc:
        return jsonify({"success": False, "message": str(exc)}), 400

    job_id = uuid.uuid4().hex
    with VIDEO_JOBS_LOCK:
        VIDEO_JOBS[job_id] = {"status": "running", "progress": 0, "message": ""}

    thread = threading.Thread(target=run_video_job, args=(job_id, data, chapters), daemon=True)
    thread.start()
    return jsonify({"success": True, "job_id": job_id, "progress_url": f"/video_progress/{job_id}"})


@app.route("/video_info", methods=["POST"])
def video_info():
    if "video" not in request.files:
        return jsonify({"success": False, "message": "请上传视频文件"}), 400

    video_file = request.files["video"]

    import tempfile
    with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as tmp:
        video_file.save(tmp.name)
        user_video_path = tmp.name

    try:
        info = creator.get_video_info(user_video_path)
        progress_height = round(info["width"] / 1920 * 90)
        return jsonify({
            "success": True,
            "width": info["width"],
            "height": info["height"],
            "fps": info["fps"],
            "progress_height": progress_height
        })
    except Exception as exc:
        return jsonify({"success": False, "message": str(exc)}), 500
    finally:
        import os
        os.unlink(user_video_path)


@app.route("/generate_video_with_video", methods=["POST"])
def generate_video_with_video():
    if "video" not in request.files:
        return jsonify({"success": False, "message": "请上传视频文件"}), 400

    if "config" not in request.form:
        return jsonify({"success": False, "message": "缺少配置"}), 400

    try:
        config = json.loads(request.form["config"])
        chapters = config.get("chapters", [])
        if not chapters:
            return jsonify({"success": False, "message": "请先添加章节"}), 400

        video_file = request.files["video"]
        import tempfile
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as tmp:
            video_file.save(tmp.name)
            user_video_path = tmp.name

        try:
            video_width, video_height = creator.get_video_resolution(user_video_path)
            progress_height = round(video_width / 1920 * 90)
            config["width"] = video_width
            config["height"] = progress_height
        except Exception:
            pass

        job_id = uuid.uuid4().hex
        with VIDEO_JOBS_LOCK:
            VIDEO_JOBS[job_id] = {"status": "running", "progress": 0, "message": ""}

        thread = threading.Thread(
            target=run_video_job,
            args=(job_id, config, chapters, user_video_path),
            daemon=True
        )
        thread.start()
        return jsonify({"success": True, "job_id": job_id})

    except Exception as exc:
        return jsonify({"success": False, "message": str(exc)}), 500


@app.route("/video_progress/<job_id>", methods=["GET"])
def video_progress(job_id):
    with VIDEO_JOBS_LOCK:
        job = VIDEO_JOBS.get(job_id)
        if not job:
            return jsonify({"success": False, "message": "\u4efb\u52a1\u4e0d\u5b58\u5728"}), 404
        return jsonify({"success": True, **job})


@app.route("/download_video", methods=["GET"])
def download_video():
    if not generated_video_path or not generated_video_path.exists():
        return jsonify({"success": False, "message": "\u8fd8\u6ca1\u6709\u751f\u6210\u89c6\u9891"}), 404
    return send_file(
        generated_video_path,
        as_attachment=True,
        download_name=f"video-progress-bar-{datetime.now():%Y%m%d-%H%M%S}.mp4",
        mimetype="video/mp4",
    )


@app.route("/health", methods=["GET"])
def health():
    return jsonify(
        {
            "ok": True,
            "ffmpeg": bool(creator.find_ffmpeg()),
            "font": creator.font_path.name if creator.font_path else "Pillow default",
        }
    )


@app.route("/output_dir", methods=["GET"])
def get_output_directory():
    return jsonify({
        "success": True,
        "output_dir": str(get_output_dir()),
        "default_dir": str(get_default_output_dir()),
    })


@app.route("/output_dir", methods=["POST"])
def set_output_directory():
    data = request.get_json(silent=True) or {}
    path = data.get("path", "")
    if not path:
        return jsonify({"success": False, "message": "路径不能为空"}), 400

    if set_output_dir(path):
        return jsonify({"success": True, "output_dir": str(get_output_dir())})
    return jsonify({"success": False, "message": "无法设置该路径"}), 400


@app.route("/gif_options", methods=["GET"])
def gif_options():
    options = [
        {"id": "none", "label": "\u4e0d\u4f7f\u7528", "url": "", "available": True, "custom": False}
    ]

    for path in sorted(CUSTOM_GIF_DIR.glob("*.gif")):
        options.append(
            {
                "id": f"custom:{path.name}",
                "label": path.stem,
                "url": custom_gif_url(path.name),
                "available": True,
                "custom": True,
            }
        )
    return jsonify({"options": options})


@app.route("/custom_gifs/<path:filename>", methods=["GET"])
def serve_custom_gif(filename):
    try:
        safe_name = safe_gif_filename(filename)
    except ValueError:
        return jsonify({"success": False, "message": "GIF \u4e0d\u5b58\u5728"}), 404
    return send_from_directory(CUSTOM_GIF_DIR, safe_name, mimetype="image/gif")


@app.route("/upload_gif", methods=["POST"])
def upload_gif():
    file = request.files.get("gif")
    if not file or not file.filename:
        return jsonify({"success": False, "message": "\u8bf7\u9009\u62e9 GIF \u6587\u4ef6"}), 400

    try:
        filename = safe_gif_filename(file.filename)
    except ValueError as exc:
        return jsonify({"success": False, "message": str(exc)}), 400

    target = CUSTOM_GIF_DIR / filename
    if target.exists():
        stem = target.stem
        suffix = target.suffix
        target = CUSTOM_GIF_DIR / f"{stem}-{uuid.uuid4().hex[:6]}{suffix}"

    file.save(target)
    try:
        with Image.open(target) as image:
            image.verify()
    except Exception:
        target.unlink(missing_ok=True)
        return jsonify({"success": False, "message": "\u4e0a\u4f20\u7684\u6587\u4ef6\u4e0d\u662f\u6709\u6548 GIF"}), 400

    return jsonify({"success": True, "id": f"custom:{target.name}", "filename": target.name})


@app.route("/delete_gif", methods=["POST"])
def delete_gif():
    data = request.get_json(silent=True) or {}
    marker_id = str(data.get("id", ""))
    if not marker_id.startswith("custom:"):
        return jsonify({"success": False, "message": "\u53ea\u80fd\u5220\u9664\u81ea\u5b9a\u4e49 GIF"}), 400

    try:
        filename = safe_gif_filename(marker_id.split(":", 1)[1])
    except ValueError as exc:
        return jsonify({"success": False, "message": str(exc)}), 400

    target = CUSTOM_GIF_DIR / filename
    if target.exists() and target.suffix.lower() == ".gif":
        target.unlink()
        return jsonify({"success": True})

    return jsonify({"success": False, "message": "\u6587\u4ef6\u4e0d\u5b58\u5728"}), 404


@app.route("/font_options", methods=["GET"])
def font_options():
    fonts = scan_system_fonts()
    for font in fonts:
        font["risky"] = is_risky_font(font["name"])
    current = get_font_setting()
    return jsonify({
        "success": True,
        "fonts": fonts,
        "current": current,
    })


@app.route("/font", methods=["GET"])
def get_font():
    return jsonify({"success": True, **get_font_setting()})


@app.route("/font", methods=["POST"])
def set_font():
    data = request.get_json(silent=True) or {}
    font_path = data.get("font_path", "")
    font_name = data.get("font_name", "默认")

    if font_path and not Path(font_path).exists():
        return jsonify({"success": False, "message": "字体文件不存在"}), 400

    if set_font_setting(font_path, font_name):
        return jsonify({"success": True, "font_path": font_path, "font_name": font_name})
    return jsonify({"success": False, "message": "设置字体失败"}), 400


if __name__ == "__main__":
    print("视频进度条生成器")
    print("打开 http://127.0.0.1:5000 使用")
    app.run(debug=True, host="0.0.0.0", port=5000)
