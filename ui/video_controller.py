"""将视频生成服务封装为独立 Qt 工作线程。"""

from __future__ import annotations

import logging
from logging import Logger
from pathlib import Path
from typing import Callable, Protocol

from PySide6.QtCore import QObject, QThread, Signal, Slot

from video.video_generator import VideoConfig, VideoGenerator


class VideoGeneratorLike(Protocol):
    """视频生成服务所需的最小接口，便于独立测试。"""

    def generate(self, image_directory: Path) -> Path: ...


GeneratorFactory = Callable[[VideoConfig, Logger], VideoGeneratorLike]


class VideoWorker(QObject):
    """运行在 Qt 后台线程中的视频生成工作对象。"""

    generated = Signal(str)
    failed = Signal(str)

    def __init__(self, logger: Logger, generator_factory: GeneratorFactory) -> None:
        super().__init__()
        self.logger = logger
        self.generator_factory = generator_factory

    @Slot(str, int, bool)
    def generate(self, image_directory: str, fps: int, delete_images: bool) -> None:
        """生成视频并通过信号返回结果。"""
        try:
            config = VideoConfig(
                fps=fps,
                delete_images_after_video=delete_images,
            )
            generator = self.generator_factory(config, self.logger)
            output_path = generator.generate(Path(image_directory))
            self.generated.emit(str(output_path))
        except Exception as error:  # FFmpeg、磁盘和配置异常不能退出工作线程
            self.logger.exception("视频生成线程失败")
            self.failed.emit(str(error))


class VideoController(QObject):
    """管理视频生成线程，并为 GUI 提供异步信号。"""

    request_generate = Signal(str, int, bool)
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

    def start(self, image_directory: Path, fps: int, delete_images: bool) -> bool:
        """异步启动视频生成。"""
        if self._running:
            return False
        self._running = True
        self.running_changed.emit(True)
        self.logger.info("视频生成任务已启动: %s", image_directory)
        self.request_generate.emit(str(image_directory), fps, delete_images)
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
