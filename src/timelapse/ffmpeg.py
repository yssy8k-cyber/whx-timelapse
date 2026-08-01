"""Small, testable wrappers around the FFmpeg command line tools."""

from __future__ import annotations

import subprocess
import re
from typing import Sequence


class FFmpegError(RuntimeError):
    """Raised when FFmpeg cannot complete an operation."""


_CREDENTIALS = re.compile(r"(r?tsps?://)([^/@\s]+):([^/@\s]+)@", re.IGNORECASE)


def _redact_credentials(text: str) -> str:
    return _CREDENTIALS.sub(r"\1***:***@", text)


def run_ffmpeg(
    args: Sequence[str],
    *,
    timeout: float | None = None,
    ffmpeg_bin: str = "ffmpeg",
) -> subprocess.CompletedProcess[str]:
    """Run FFmpeg without a shell and return its completed process."""

    command = [ffmpeg_bin, *args]
    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
    except FileNotFoundError as exc:
        raise FFmpegError(
            f"找不到 FFmpeg 可执行文件: {ffmpeg_bin!r}，请安装 FFmpeg 或通过 --ffmpeg 指定路径。"
        ) from exc
    except subprocess.TimeoutExpired as exc:
        raise FFmpegError(f"FFmpeg 执行超时（{timeout:g} 秒）。") from exc

    if result.returncode != 0:
        detail = _redact_credentials((result.stderr or result.stdout or "未知错误").strip())
        raise FFmpegError(f"FFmpeg 执行失败（退出码 {result.returncode}）: {detail}")
    return result
