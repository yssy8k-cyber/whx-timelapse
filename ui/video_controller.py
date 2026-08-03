"""将视频生成服务封装为独立 Qt 工作线程。"""

from __future__ import annotations

import logging
from datetime import datetime
from logging import Logger
from pathlib import Path
from collections.abc import Sequence
from typing import Callable, Protocol

from PySide6.QtCore import QObject, QThread, Signal, Slot

from video.video_generator import VideoConfig, VideoGenerator


class VideoGeneratorLike(Protocol):
    """视频生成服务所需的最小接口，便于独立测试。"""

    def generate(self, image_directory: Path) -> Path: ...

    def generate_range(self, image_directories: Sequence[Path], output_path: Path) -> Path: ...


GeneratorFactory = Callable[[VideoConfig, Logger], VideoGeneratorLike]


class VideoWorker(QObject):
    """运行在 Qt 后台线程中的视频生成工作对象。"""

    generated = Signal(str)
    failed = Signal(str)

    def __init__(self, logger: Logger, generator_factory: GeneratorFactory) -> None:
        super().__init__()
        self.logger = logger
        self.generator_factory = generator_factory

    @Slot(object, int, bool, str, str, int, str, str, str, str, bool)
    def generate(
        self,
        image_directories: object,
        fps: int,
        delete_images: bool,
        output_path: str,
        retention_policy: str,
        retention_days: int,
        image_root_directory: str,
        overwrite_policy: str,
        image_start_datetime: str,
        image_end_datetime: str,
        log_generation: bool,
    ) -> None:
        """生成视频并通过信号返回结果。"""
        try:
            config = VideoConfig(
                fps=fps,
                delete_images_after_video=delete_images,
                image_retention_policy=retention_policy,
                image_retention_days=retention_days,
                image_root_directory=Path(image_root_directory) if image_root_directory else None,
                overwrite_policy=overwrite_policy,
                log_generation=log_generation,
                image_start_datetime=(
                    datetime.fromisoformat(image_start_datetime)
                    if image_start_datetime
                    else None
                ),
                image_end_datetime=(
                    datetime.fromisoformat(image_end_datetime)
                    if image_end_datetime
                    else None
                ),
            )
            generator = self.generator_factory(config, self.logger)
            directories = _as_paths(image_directories)
            if output_path and hasattr(generator, "generate_range"):
                generated_path = generator.generate_range(directories, Path(output_path))
            elif output_path:
                generated_path = generator.generate(directories[0], Path(output_path))
            else:
                generated_path = generator.generate(directories[0])
            self.generated.emit(str(generated_path))
        except Exception as error:  # FFmpeg、磁盘和配置异常不能退出工作线程
            self.logger.exception("视频生成线程失败")
            self.failed.emit(str(error))


class VideoController(QObject):
    """管理视频生成线程，并为 GUI 提供异步信号。"""

    request_generate = Signal(object, int, bool, str, str, int, str, str, str, str, bool)
    generated = Signal(str)
    failed = Signal(str)
    running_changed = Signal(bool)

    def __init__(
        self,
        logger: Logger | None = None,
        parent: QObject | None = None,
        generator_factory: GeneratorFactory | None = None,
    ) -> None:
        super().__init__(parent)
        self.logger = logger or logging.getLogger(__name__)
        factory = generator_factory or self._create_generator
        self._thread = QThread(self)
        self._worker = VideoWorker(self.logger, factory)
        self._worker.moveToThread(self._thread)
        self.request_generate.connect(self._worker.generate)
        self._worker.generated.connect(self._on_generated)
        self._worker.failed.connect(self._on_failed)
        self._thread.finished.connect(self._worker.deleteLater)
        self._running = False
        self._thread.start()

    @property
    def is_running(self) -> bool:
        """返回当前是否正在生成视频。"""
        return self._running

    def start(
        self,
        image_directory: Path | Sequence[Path],
        fps: int,
        delete_images: bool,
        output_path: Path | None = None,
        retention_policy: str = "keep_all",
        retention_days: int = 7,
        image_root_directory: Path | None = None,
        overwrite_policy: str = "overwrite",
        image_start_datetime: datetime | None = None,
        image_end_datetime: datetime | None = None,
        log_generation: bool = True,
    ) -> bool:
        """异步启动视频生成。"""
        if self._running:
            return False
        self._running = True
        self.running_changed.emit(True)
        directories = _as_paths(image_directory)
        if log_generation:
            self.logger.info("视频生成任务已启动: %s", directories)
        self.request_generate.emit(
            directories,
            fps,
            delete_images,
            str(output_path) if output_path else "",
            retention_policy,
            retention_days,
            str(image_root_directory) if image_root_directory else "",
            overwrite_policy,
            image_start_datetime.isoformat() if image_start_datetime else "",
            image_end_datetime.isoformat() if image_end_datetime else "",
            log_generation,
        )
        return True

    def shutdown(self) -> None:
        """等待当前生成任务结束后释放 Qt 线程。"""
        if self._running:
            self.logger.info("正在等待视频生成任务结束")
        self._thread.quit()
        self._thread.wait()

    def _on_generated(self, output_path: str) -> None:
        self._running = False
        self.running_changed.emit(False)
        self.generated.emit(output_path)

    def _on_failed(self, message: str) -> None:
        self._running = False
        self.running_changed.emit(False)
        self.failed.emit(message)

    @staticmethod
    def _create_generator(config: VideoConfig, logger: Logger) -> VideoGenerator:
        return VideoGenerator(config, logger)


def _as_paths(value: Path | Sequence[Path] | object) -> list[Path]:
    """统一单目录和多目录输入，避免 Qt 信号携带 Path 类型。"""
    if isinstance(value, Path):
        return [value]
    if isinstance(value, (str, bytes)):
        return [Path(value)]
    if isinstance(value, Sequence):
        paths = [Path(item) for item in value]
        if paths:
            return paths
    raise ValueError("至少需要一个图片目录")
