"""Periodic single-frame capture from an RTSP stream."""

from __future__ import annotations

import logging
import os
import threading
import time
import uuid
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from .ffmpeg import run_ffmpeg

LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True)
class CaptureConfig:
    rtsp_url: str
    output_dir: Path
    interval: float = 10.0
    count: int | None = None
    duration: float | None = None
    ffmpeg_bin: str = "ffmpeg"
    transport: str = "tcp"
    timeout: float = 30.0
    jpeg_quality: int = 2

    def validate(self) -> None:
        if not self.rtsp_url:
            raise ValueError("RTSP 地址不能为空。")
        if self.interval <= 0:
            raise ValueError("抽帧间隔必须大于 0 秒。")
        if self.count is not None and self.count <= 0:
            raise ValueError("抽帧数量必须大于 0。")
        if self.duration is not None and self.duration <= 0:
            raise ValueError("持续时间必须大于 0 秒。")
        if self.timeout <= 0:
            raise ValueError("单次连接超时必须大于 0 秒。")
        if self.count is not None and self.duration is not None:
            raise ValueError("--count 和 --duration 只能二选一。")
        if self.transport not in {"tcp", "udp", "http", "https"}:
            raise ValueError("RTSP 传输方式必须是 tcp、udp、http 或 https。")
        if not 1 <= self.jpeg_quality <= 31:
            raise ValueError("JPEG 质量必须在 1 到 31 之间，数字越小质量越高。")


def _safe_stream_label(rtsp_url: str) -> str:
    """Return a log-safe label without exposing credentials."""

    if "@" in rtsp_url and "://" in rtsp_url:
        prefix, address = rtsp_url.split("@", 1)
        scheme = prefix.split("://", 1)[0]
        return f"{scheme}://***@{address}"
    return rtsp_url


def build_snapshot_args(config: CaptureConfig, destination: Path) -> list[str]:
    """Build the one-shot FFmpeg command used for a single snapshot."""

    return [
        "-hide_banner",
        "-loglevel",
        "error",
        "-rtsp_transport",
        config.transport,
        "-rw_timeout",
        str(int(config.timeout * 1_000_000)),
        "-i",
        config.rtsp_url,
        "-map",
        "0:v:0",
        "-frames:v",
        "1",
        "-q:v",
        str(config.jpeg_quality),
        "-an",
        "-f",
        "image2",
        "-y",
        str(destination),
    ]


def capture_one(config: CaptureConfig, destination: Path) -> Path:
    """Capture one frame to ``destination`` and return it after success."""

    config.output_dir.mkdir(parents=True, exist_ok=True)
    temporary = config.output_dir / f".{destination.name}.{uuid.uuid4().hex}.part.jpg"
    try:
        run_ffmpeg(
            build_snapshot_args(config, temporary),
            timeout=config.timeout + 5,
            ffmpeg_bin=config.ffmpeg_bin,
        )
        if not temporary.is_file() or temporary.stat().st_size == 0:
            raise RuntimeError("FFmpeg 未生成有效图片。")
        os.replace(temporary, destination)
        return destination
    finally:
        temporary.unlink(missing_ok=True)


def capture(config: CaptureConfig, stop_event: threading.Event | None = None) -> list[Path]:
    """Capture immediately, then periodically until count/duration is reached."""

    config.validate()
    config.output_dir.mkdir(parents=True, exist_ok=True)
    LOGGER.info("开始从 %s 抽帧，间隔 %.3g 秒。", _safe_stream_label(config.rtsp_url), config.interval)

    captured: list[Path] = []
    started = time.monotonic()
    next_capture = started
    while True:
        if stop_event is not None and stop_event.is_set():
            LOGGER.info("收到停止请求。")
            break
        wait_seconds = next_capture - time.monotonic()
        if wait_seconds > 0:
            if stop_event is None:
                time.sleep(wait_seconds)
            else:
                stop_event.wait(wait_seconds)
                if stop_event.is_set():
                    LOGGER.info("收到停止请求。")
                    break
        if config.duration is not None and time.monotonic() - started >= config.duration:
            break

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        destination = config.output_dir / f"frame_{timestamp}.jpg"
        try:
            capture_one(config, destination)
        except Exception:
            LOGGER.exception("抽帧失败，稍后将按间隔重试。")
        else:
            captured.append(destination)
            LOGGER.info("已保存第 %d 帧: %s", len(captured), destination)
            if config.count is not None and len(captured) >= config.count:
                break

        next_capture += config.interval
        if next_capture < time.monotonic():
            next_capture = time.monotonic() + config.interval

    LOGGER.info("抽帧结束，共生成 %d 张图片。", len(captured))
    return captured
