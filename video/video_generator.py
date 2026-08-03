"""基于图片目录生成 MP4(H.264) 延时视频。"""

from __future__ import annotations

import logging
import os
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from datetime import date, datetime, timedelta
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
    """视频生成和图片清理配置。"""

    fps: int = 24
    delete_images_after_video: bool = False
    image_retention_policy: str = "keep_all"
    image_retention_days: int = 7
    image_root_directory: Path | None = None
    overwrite_policy: str = "overwrite"
    log_generation: bool = True
    image_start_datetime: datetime | None = None
    image_end_datetime: datetime | None = None
    ffmpeg_path: str | Path = "ffmpeg"

    def __post_init__(self) -> None:
        if self.fps not in (15, 24, 30, 60):
            raise ValueError("视频 FPS 只支持 15、24、30 或 60")
        if self.image_retention_policy not in {
            "keep_all",
            "delete_after_video",
            "keep_recent_days",
        }:
            raise ValueError("图片保存策略无效")
        if self.delete_images_after_video:
            object.__setattr__(self, "image_retention_policy", "delete_after_video")
        if self.image_retention_days < 1:
            raise ValueError("保留图片天数必须大于 0")
        if self.overwrite_policy not in {"overwrite", "rename", "prompt"}:
            raise ValueError("视频覆盖策略无效")


class VideoGenerator:
    """查找图片、调用 FFmpeg 并在成功后执行图片管理。"""

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
        """为一个日期目录生成视频，保留旧版调用接口。"""
        image_directory = Path(image_directory)
        target = output_path or (
            image_directory.parent / f"{image_directory.name}.mp4"
        )
        return self.generate_range([image_directory], target)

    def generate_range(
        self,
        image_directories: Sequence[Path],
        output_path: Path,
    ) -> Path:
        """合成多个日期目录中的图片，并返回最终视频路径。"""
        directories = [Path(directory) for directory in image_directories]
        images = self._find_images_in_directories(directories)
        target = self.resolve_output_path(Path(output_path), self.config.overwrite_policy)
        target.parent.mkdir(parents=True, exist_ok=True)

        # 使用硬链接建立连续序列，跨磁盘时回退到复制。
        # 该过程不会改变原始图片。
        with tempfile.TemporaryDirectory(prefix="timelapse-sequence-") as temp_dir:
            sequence_directory = Path(temp_dir)
            self._stage_images(images, sequence_directory)
            arguments = self._build_arguments(sequence_directory, target)
            self._run_ffmpeg(arguments, target)

        self._apply_image_policy(images)
        if self.config.log_generation:
            self.logger.info("视频生成成功: %s", target)
        return target

    @staticmethod
    def resolve_output_path(target: Path, policy: str) -> Path:
        """根据覆盖策略返回可写的输出路径。"""
        if policy == "overwrite" or not target.exists():
            return target
        if policy == "prompt":
            # GUI 会在启动任务前处理提示；非 GUI 调用采用重命名保证安全。
            policy = "rename"
        if policy != "rename":
            raise ValueError("视频覆盖策略无效")
        counter = 1
        while True:
            candidate = target.with_name(f"{target.stem}_{counter:03d}{target.suffix}")
            if not candidate.exists():
                return candidate
            counter += 1

    def _find_images_in_directories(self, directories: Sequence[Path]) -> list[Path]:
        images: list[Path] = []
        for directory in directories:
            if not directory.exists():
                continue
            if not directory.is_dir():
                raise VideoGenerationError(f"图片路径不是目录: {directory}")
            for path in directory.iterdir():
                if not path.is_file() or path.suffix.lower() != ".jpg":
                    continue
                if self._is_in_datetime_filter(path):
                    images.append(path)
        if not images:
            names = ", ".join(str(path) for path in directories)
            raise VideoGenerationError(f"图片目录中没有 JPEG 文件: {names}")
        return sorted(images)

    def _is_in_datetime_filter(self, image_path: Path) -> bool:
        """按图片文件名筛选精确时间范围，无法解析时保留图片。"""
        start = self.config.image_start_datetime
        end = self.config.image_end_datetime
        if start is None and end is None:
            return True
        try:
            captured_at = datetime.strptime(image_path.stem, "%Y%m%d_%H%M%S")
        except ValueError:
            return True
        if start is not None and captured_at < start:
            return False
        if end is not None and captured_at > end:
            return False
        return True

    @staticmethod
    def _stage_images(images: Sequence[Path], target_directory: Path) -> None:
        target_directory.mkdir(parents=True, exist_ok=True)
        for index, image_path in enumerate(images, start=1):
            staged_path = target_directory / f"{index:08d}.jpg"
            try:
                os.link(image_path, staged_path)
            except OSError:
                shutil.copy2(image_path, staged_path)

    def _build_arguments(self, image_directory: Path, output_path: Path) -> list[str]:
        """构造不依赖 shell 的 FFmpeg 参数。"""
        # 使用 image2 的连续编号序列，避免 Windows FFmpeg 不支持 glob。
        image_pattern = str(image_directory / "%08d.jpg")
        return [
            "-hide_banner",
            "-loglevel",
            "error",
            "-y",
            "-framerate",
            str(self.config.fps),
            "-start_number",
            "1",
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

    def _run_ffmpeg(self, arguments: list[str], target: Path) -> None:
        try:
            result = self.runner.run(arguments)
            if result.returncode != 0:
                message = result.stderr.strip() or "FFmpeg 返回失败状态"
                raise FFmpegExecutionError(message)
        except FFmpegExecutionError:
            self.logger.exception("视频生成失败: %s", target)
            raise
        except Exception as error:
            self.logger.exception("调用 FFmpeg 时发生未预期异常")
            raise FFmpegExecutionError(str(error)) from error
        if not target.exists():
            message = f"FFmpeg 返回成功，但未找到输出文件: {target}"
            self.logger.error(message)
            raise VideoGenerationError(message)

    def _apply_image_policy(self, images: Sequence[Path]) -> None:
        policy = self.config.image_retention_policy
        if policy == "delete_after_video":
            self._delete_images(images)
        elif policy == "keep_recent_days" and self.config.image_root_directory:
            self._cleanup_old_images(self.config.image_root_directory)

    def _delete_images(self, images: Sequence[Path]) -> None:
        for image_path in images:
            try:
                image_path.unlink()
                if self.config.log_generation:
                    self.logger.info("删除图片: %s", image_path)
            except OSError as error:
                self.logger.error("删除图片失败: %s (%s)", image_path, error)

    def _cleanup_old_images(self, image_root: Path) -> None:
        cutoff = date.today() - timedelta(days=self.config.image_retention_days - 1)
        if not image_root.exists() or not image_root.is_dir():
            return
        for directory in image_root.iterdir():
            if not directory.is_dir():
                continue
            try:
                directory_date = date.fromisoformat(directory.name)
            except ValueError:
                continue
            if directory_date >= cutoff:
                continue
            for image_path in directory.glob("*.jpg"):
                try:
                    image_path.unlink()
                    if self.config.log_generation:
                        self.logger.info("按保留天数删除图片: %s", image_path)
                except OSError as error:
                    self.logger.error("清理图片失败: %s (%s)", image_path, error)


__all__ = ["VideoConfig", "VideoGenerationError", "VideoGenerator"]
