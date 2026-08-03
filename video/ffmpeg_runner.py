"""FFmpeg 子进程调用封装。"""

from __future__ import annotations

import logging
import subprocess
import sys
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
        self.logger.debug("FFmpeg 命令: %s", _format_command(command))
        try:
            completed = subprocess.run(
                command,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                check=False,
                **_windows_process_options(),
            )
        except FileNotFoundError as error:
            raise FFmpegExecutionError(
                f"找不到 FFmpeg: {self.executable}"
            ) from error
        except OSError as error:
            raise FFmpegExecutionError(f"启动 FFmpeg 失败: {error}") from error

        if completed.returncode != 0:
            error_message = _format_failure_message(command, completed)
            self.logger.error(error_message)
            raise FFmpegExecutionError(error_message)
        return completed


def _windows_process_options() -> dict[str, object]:
    """在 Windows 隐藏 FFmpeg 控制台窗口，并保持其他平台参数为空。"""
    if not sys.platform.startswith("win"):
        return {}
    startup_info = subprocess.STARTUPINFO()
    startup_info.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    return {
        "startupinfo": startup_info,
        "creationflags": getattr(subprocess, "CREATE_NO_WINDOW", 0),
    }


def _format_command(command: Sequence[str]) -> str:
    """为日志和错误提示生成可读的命令行文本。"""
    return " ".join(_quote_argument(argument) for argument in command)


def _quote_argument(argument: str) -> str:
    """为包含空格或特殊字符的参数添加双引号。"""
    if not argument or any(character.isspace() for character in argument):
        return f'"{argument.replace(chr(34), chr(92) + chr(34))}"'
    return argument


def _format_failure_message(
    command: Sequence[str],
    completed: subprocess.CompletedProcess[str],
) -> str:
    """合并 FFmpeg 的两个输出流，避免丢失关键诊断信息。"""
    stderr = (completed.stderr or "").strip()
    stdout = (completed.stdout or "").strip()
    details: list[str] = [
        f"FFmpeg 执行失败，退出码: {completed.returncode}",
        f"命令: {_format_command(command)}",
    ]
    if stderr:
        details.append(f"FFmpeg 错误输出: {stderr}")
    if stdout:
        details.append(f"FFmpeg 标准输出: {stdout}")
    if not stderr and not stdout:
        details.append(
            "FFmpeg 未返回诊断信息。请检查图片目录是否包含 JPEG、输出目录权限，"
            "以及杀毒软件是否拦截了 FFmpeg。"
        )
    return "\n".join(details)


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
