"""基于日期图片目录生成 MP4 延时视频。"""

from __future__ import annotations

import logging
import subprocess
from dataclasses import dataclass
from logging import Logger
from pathlib import Path
from typing import Protocol, Sequence

from .ffmpeg_runner import FFmpegExecutionError, FFmpegRunner


class VideoGenerationError(RuntimeError):
    """视频生成前置条件或输出校验失败。"""


class FFmpegCommandRunner(Protocol):
    """可注入的 FFmpeg 执行接口。"""

    def run(self, arguments: Sequence[str]) -> subprocess.CompletedProcess[str]: ...


@dataclass(frozen=True)
class VideoConfig:
    """视频生成配置。"""

    fps: int = 24
    delete_images_after_video: bool = False
    ffmpeg_path: str | Path = "ffmpeg"

    def __post_init__(self) -> None:
        if self.fps not in (15, 24, 30, 60):
            raise ValueError("视频 FPS 只支持 15、24、30 或 60")


class VideoGenerator:
    """查找图片并调用 FFmpeg 生成 H.264 MP4。"""

    def __init__(
        self,
        config: VideoConfig,
        logger: Logger | None = None,
        runner: FFmpegCommandRunner | None = None,
    ) -> None:
        self.config = config
        self.logger = logger or logging.getLogger(__name__)
        self.runner = runner or FFmpegRunner(config.ffmpeg_path, self.logger)

    def generate(self, image_directory: Path, output_path: Path | None = None) -> Path:
        """为一个日期目录生成视频，成功后返回 MP4 路径。"""
        image_directory = Path(image_directory)
        images = self._find_images(image_directory)
        if not images:
            raise VideoGenerationError(f"图片目录中没有 JPEG 文件: {image_directory}")

        target = output_path or image_directory.parent / f"{image_directory.name}.mp4"
        target = Path(target)
        target.parent.mkdir(parents=True, exist_ok=True)
        arguments = self._build_arguments(image_directory, target)

        try:
            result = self.runner.run(arguments)
            if result.returncode != 0:
                error_message = result.stderr.strip() or "FFmpeg 返回失败状态"
                raise FFmpegExecutionError(error_message)
        except FFmpegExecutionError:
            self.logger.exception("视频生成失败: %s", target)
            raise
        except Exception as error:
            self.logger.exception("调用 FFmpeg 时发生未预期异常")
            raise FFmpegExecutionError(str(error)) from error

        if not target.exists():
            error = f"FFmpeg 返回成功，但未找到输出文件: {target}"
            self.logger.error(error)
            raise VideoGenerationError(error)

        self.logger.info("视频生成成功: %s", target)
        if self.config.delete_images_after_video:
            self._delete_images(images)
        return target

    @staticmethod
    def _find_images(image_directory: Path) -> list[Path]:
        if not image_directory.exists() or not image_directory.is_dir():
            raise VideoGenerationError(f"图片目录不存在: {image_directory}")
        return sorted(
            path
            for path in image_directory.iterdir()
            if path.is_file() and path.suffix.lower() == ".jpg"
        )

    def _build_arguments(self, image_directory: Path, output_path: Path) -> list[str]:
        """构造不依赖 shell 的 FFmpeg 参数。"""
        image_pattern = (image_directory / "*.jpg").as_posix()
        return [
            "-hide_banner",
            "-loglevel",
            "error",
            "-y",
            "-framerate",
            str(self.config.fps),
            "-pattern_type",
            "glob",
            "-i",
            image_pattern,
            "-vf",
            "scale=trunc(iw/2)*2:trunc(ih/2)*2",
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            "-movflags",
            "+faststart",
            str(output_path),
        ]

    def _delete_images(self, images: list[Path]) -> None:
        """仅在视频成功后删除本次使用的图片。"""
        for image_path in images:
            try:
                image_path.unlink()
                self.logger.info("删除图片: %s", image_path)
            except OSError as error:
                self.logger.error("删除图片失败: %s (%s)", image_path, error)
