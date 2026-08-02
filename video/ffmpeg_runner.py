"""FFmpeg 子进程调用封装。"""

from __future__ import annotations

import logging
import subprocess
from logging import Logger
from pathlib import Path
from typing import Sequence


class FFmpegExecutionError(RuntimeError):
    """FFmpeg 不可执行或返回失败状态。"""


class FFmpegRunner:
    """执行 FFmpeg 命令并统一转换异常。"""

    def __init__(self, executable: str | Path = "ffmpeg", logger: Logger | None = None) -> None:
        self.executable = resolve_ffmpeg_path(executable)
        self.logger = logger or logging.getLogger(__name__)

    def run(self, arguments: Sequence[str]) -> subprocess.CompletedProcess[str]:
        """执行 FFmpeg 参数；失败时抛出 FFmpegExecutionError。"""
        command = [self.executable, *arguments]
        self.logger.info("开始执行 FFmpeg 视频生成")
        try:
            completed = subprocess.run(
                command,
                capture_output=True,
                text=True,
                check=False,
            )
        except FileNotFoundError as error:
            raise FFmpegExecutionError(
                f"找不到 FFmpeg: {self.executable}"
            ) from error
        except OSError as error:
            raise FFmpegExecutionError(f"启动 FFmpeg 失败: {error}") from error

        if completed.returncode != 0:
            error_message = completed.stderr.strip() or "FFmpeg 未提供错误信息"
            raise FFmpegExecutionError(error_message)
        return completed


def resolve_ffmpeg_path(executable: str | Path) -> str:
    """优先使用 imageio-ffmpeg 提供的跨平台 FFmpeg。"""
    requested_path = str(executable)
    if requested_path != "ffmpeg":
        return requested_path
    try:
        import imageio_ffmpeg

        return imageio_ffmpeg.get_ffmpeg_exe()
    except (ImportError, RuntimeError, OSError):
        return requested_path
