"""End-to-end capture, render, and optional external post-processing."""

from __future__ import annotations

import logging
import shlex
import subprocess
from pathlib import Path

from .capture import CaptureConfig, capture
from .render import render

LOGGER = logging.getLogger(__name__)


def capture_and_render(
    capture_config: CaptureConfig,
    stop_event,
    output_video: Path,
    *,
    fps: float = 24.0,
    crf: int = 18,
    preset: str = "medium",
    overwrite: bool = False,
) -> tuple[list[Path], Path | None]:
    """Capture frames and render them unless the operator stopped the job."""

    captured = capture(capture_config, stop_event)
    if stop_event.is_set():
        return captured, None
    if not captured:
        raise RuntimeError("没有成功采集到图片，无法自动合成视频。")
    rendered = render(
        capture_config.output_dir,
        output_video,
        images=captured,
        fps=fps,
        ffmpeg_bin=capture_config.ffmpeg_bin,
        crf=crf,
        preset=preset,
        overwrite=overwrite,
    )
    return captured, rendered


def run_postprocess(command: str, input_video: Path, output_video: Path) -> Path:
    """Run an external AI/video tool command using {input} and {output} placeholders."""

    tokens = [token.replace("{input}", str(input_video)).replace("{output}", str(output_video)) for token in shlex.split(command)]
    if not tokens:
        raise ValueError("后处理命令不能为空。")
    if "{input}" not in command or "{output}" not in command:
        raise ValueError("后处理命令必须同时包含 {input} 和 {output} 占位符。")
    try:
        subprocess.run(tokens, check=True)
    except subprocess.CalledProcessError as exc:
        raise RuntimeError(f"后处理命令失败（退出码 {exc.returncode}）。") from exc
    if not output_video.is_file() or output_video.stat().st_size == 0:
        raise RuntimeError(f"后处理命令未生成有效输出: {output_video}")
    return output_video


def run_pipeline(
    capture_config: CaptureConfig,
    output_video: Path,
    *,
    fps: float = 24.0,
    crf: int = 18,
    preset: str = "medium",
    overwrite: bool = False,
    postprocess_command: str | None = None,
) -> Path:
    """Capture frames, render a video, and optionally invoke a post-processor."""

    captured = capture(capture_config)
    rendered = render(
        capture_config.output_dir,
        output_video,
        images=captured,
        fps=fps,
        ffmpeg_bin=capture_config.ffmpeg_bin,
        crf=crf,
        preset=preset,
        overwrite=overwrite,
    )
    if not postprocess_command:
        return rendered

    processed = rendered.with_name(f"{rendered.stem}_processed{rendered.suffix}")
    LOGGER.info("开始执行外部后处理命令，输入视频: %s", rendered)
    return run_postprocess(postprocess_command, rendered, processed)
