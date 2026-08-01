"""Render timestamped still images into an MP4 timelapse."""

from __future__ import annotations

import os
import tempfile
import uuid
from pathlib import Path
from typing import Sequence

from .ffmpeg import run_ffmpeg

IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png"}


def find_images(input_dir: Path) -> list[Path]:
    """Find supported images in lexical order, which preserves timestamp order."""

    return sorted(
        (path for path in input_dir.iterdir() if path.is_file() and path.suffix.lower() in IMAGE_SUFFIXES),
        key=lambda path: path.name,
    )


def _concat_line(path: Path) -> str:
    # FFmpeg concat files use single-quoted paths; escape backslashes and quotes.
    escaped = str(path.resolve()).replace("\\", "\\\\").replace("'", "'\\''")
    return f"file '{escaped}'"


def build_concat_manifest(images: list[Path], fps: float) -> str:
    """Create concat-demuxer contents with a fixed duration per still image."""

    duration = 1 / fps
    lines: list[str] = []
    for image in images:
        lines.extend([_concat_line(image), f"duration {duration:.9f}"])
    # The concat demuxer ignores the final duration unless the last file is repeated.
    lines.append(_concat_line(images[-1]))
    return "\n".join(lines) + "\n"


def render(
    input_dir: Path,
    output: Path,
    *,
    images: Sequence[Path] | None = None,
    fps: float = 24.0,
    ffmpeg_bin: str = "ffmpeg",
    crf: int = 18,
    preset: str = "medium",
    overwrite: bool = False,
) -> Path:
    """Render all still images in ``input_dir`` to an H.264 MP4."""

    if fps <= 0:
        raise ValueError("输出帧率必须大于 0。")
    if not 0 <= crf <= 51:
        raise ValueError("CRF 必须在 0 到 51 之间。")
    if not input_dir.is_dir():
        raise ValueError(f"输入目录不存在: {input_dir}")
    images = list(find_images(input_dir) if images is None else images)
    if not images:
        raise ValueError(f"输入目录中没有 JPG、JPEG 或 PNG 图片: {input_dir}")
    output = output.resolve()
    if output.exists() and not overwrite:
        raise FileExistsError(f"输出文件已存在: {output}（使用 --overwrite 覆盖）")
    output.parent.mkdir(parents=True, exist_ok=True)

    temp_output = output.parent / f".{output.stem}.{uuid.uuid4().hex}.part.mp4"
    try:
        with tempfile.TemporaryDirectory(prefix="timelapse-") as temp_dir:
            manifest = Path(temp_dir) / "concat.txt"
            manifest.write_text(build_concat_manifest(images, fps), encoding="utf-8")
            args = [
                "-hide_banner",
                "-loglevel",
                "error",
                "-f",
                "concat",
                "-safe",
                "0",
                "-i",
                str(manifest),
                "-map",
                "0:v:0",
                "-vf",
                "scale=trunc(iw/2)*2:trunc(ih/2)*2",
                "-r",
                f"{fps:g}",
                "-c:v",
                "libx264",
                "-preset",
                preset,
                "-crf",
                str(crf),
                "-pix_fmt",
                "yuv420p",
                "-movflags",
                "+faststart",
                "-an",
                "-y" if overwrite else "-n",
                str(temp_output),
            ]
            run_ffmpeg(args, ffmpeg_bin=ffmpeg_bin)
        if not temp_output.is_file() or temp_output.stat().st_size == 0:
            raise RuntimeError("FFmpeg 未生成有效视频。")
        os.replace(temp_output, output)
        return output
    finally:
        temp_output.unlink(missing_ok=True)
