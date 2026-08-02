"""将截图线程封装为可供 Qt 界面使用的控制器。"""

from __future__ import annotations

import logging
from logging import Logger
from pathlib import Path

from PySide6.QtCore import QObject, Signal

from capture.capture_worker import CaptureConfig, CaptureWorker, FrameProvider


class QtCaptureController(QObject):
    """隔离截图线程和 GUI 线程，所有结果通过 Qt 信号传递。"""

    capture_succeeded = Signal(str)
    capture_failed = Signal(str)
    running_changed = Signal(bool)

    def __init__(
        self,
        frame_provider: FrameProvider,
        logger: Logger | None = None,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self.frame_provider = frame_provider
        self.logger = logger or logging.getLogger(__name__)
        self._worker: CaptureWorker | None = None

    @property
    def is_running(self) -> bool:
        """返回截图线程是否正在运行。"""
        return self._worker is not None and self._worker.is_running

    def start(self, interval_seconds: float, jpeg_quality: int, output_directory: Path) -> bool:
        """创建并启动截图线程。"""
        if self.is_running:
            return False
        config = CaptureConfig(interval_seconds, jpeg_quality, output_directory)
        self._worker = CaptureWorker(
            frame_provider=self.frame_provider,
            config=config,
            logger=self.logger,
            on_success=self._handle_success,
            on_failure=self._handle_failure,
        )
        started = self._worker.start()
        if started:
            self.running_changed.emit(True)
        return started

    def stop(self) -> bool:
        """停止截图线程并等待其释放资源。"""
        if self._worker is None:
            return True
        stopped = self._worker.stop()
        if stopped:
            self._worker = None
            self.running_changed.emit(False)
        return stopped

    def _handle_success(self, image_path: Path) -> None:
        """将工作线程回调转换为 Qt 信号。"""
        self.capture_succeeded.emit(str(image_path))

    def _handle_failure(self, error: Exception) -> None:
        self.capture_failed.emit(str(error))
