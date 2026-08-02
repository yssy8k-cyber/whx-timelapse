"""独立线程中的定时截图工作器。"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime
from logging import Logger
from pathlib import Path
from threading import Event, Lock, Thread, current_thread
from time import monotonic
from typing import Callable

from utils.image_types import Frame

from .image_storage import ImageStorage


FrameProvider = Callable[[], Frame | None]
CaptureSuccessCallback = Callable[[Path], None]
CaptureFailureCallback = Callable[[Exception], None]


@dataclass(frozen=True)
class CaptureConfig:
    """截图线程所需的运行配置。"""

    interval_seconds: float = 60
    jpeg_quality: int = 95
    output_directory: Path = Path(r"D:\Timelapse")

    def __post_init__(self) -> None:
        if self.interval_seconds <= 0:
            raise ValueError("截图间隔必须大于 0 秒")
        if not 1 <= self.jpeg_quality <= 100:
            raise ValueError("JPEG 质量必须在 1 到 100 之间")


class CaptureWorker:
    """按固定间隔取帧并保存图片，线程异常不会传播到 GUI。"""

    def __init__(
        self,
        frame_provider: FrameProvider,
        config: CaptureConfig,
        logger: Logger | None = None,
        on_success: CaptureSuccessCallback | None = None,
        on_failure: CaptureFailureCallback | None = None,
    ) -> None:
        self.frame_provider = frame_provider
        self.config = config
        self.logger = logger or logging.getLogger(__name__)
        self.on_success = on_success
        self.on_failure = on_failure
        self._stop_event = Event()
        self._state_lock = Lock()
        self._thread: Thread | None = None
        self._storage = ImageStorage(
            config.output_directory,
            config.jpeg_quality,
            self.logger,
        )

    @property
    def is_running(self) -> bool:
        """返回截图线程是否仍在运行。"""
        with self._state_lock:
            return self._thread is not None and self._thread.is_alive()

    def start(self) -> bool:
        """启动截图线程；已经运行时返回 False。"""
        with self._state_lock:
            if self._thread is not None and self._thread.is_alive():
                return False
            self._stop_event.clear()
            self._thread = Thread(
                target=self._run,
                name="timelapse-capture",
                daemon=True,
            )
            self._thread.start()
        self.logger.info("截图线程已启动，间隔 %.2f 秒", self.config.interval_seconds)
        return True

    def stop(self, timeout: float = 5.0) -> bool:
        """请求停止并等待线程退出，超时返回 False。"""
        with self._state_lock:
            thread = self._thread
        if thread is None:
            return True

        self._stop_event.set()
        if thread is not current_thread():
            thread.join(timeout)
        stopped = not thread.is_alive()
        if stopped:
            with self._state_lock:
                if self._thread is thread:
                    self._thread = None
            self.logger.info("截图线程已停止")
        else:
            self.logger.warning("截图线程停止超时")
        return stopped

    def _run(self) -> None:
        next_capture = monotonic()
        while not self._stop_event.wait(max(0.0, next_capture - monotonic())):
            self._capture_once(datetime.now())
            next_capture += self.config.interval_seconds
            current_time = monotonic()
            if next_capture <= current_time:
                next_capture = current_time + self.config.interval_seconds

        self.logger.info("截图工作循环已退出")

    def _capture_once(self, captured_at: datetime) -> None:
        """执行一次取帧和保存，单次失败不影响后续周期。"""
        try:
            frame = self.frame_provider()
            if frame is None:
                raise RuntimeError("摄像头未返回图像帧")
            image_path = self._storage.save_frame(frame, captured_at)
            self._notify_success(image_path)
        except Exception as error:  # 网络、OpenCV 和磁盘异常均不能终止工作循环
            self.logger.exception("截图失败: %s", error)
            self._notify_failure(error)

    def _notify_success(self, image_path: Path) -> None:
        if self.on_success is None:
            return
        try:
            self.on_success(image_path)
        except Exception:
            self.logger.exception("截图成功回调执行失败")

    def _notify_failure(self, error: Exception) -> None:
        if self.on_failure is None:
            return
        try:
            self.on_failure(error)
        except Exception:
            self.logger.exception("截图失败回调执行失败")
