"""每日自动生成调度器的 Qt 信号桥接层。"""

from __future__ import annotations

from datetime import date, datetime
import logging
from logging import Logger

from PySide6.QtCore import QObject, Signal

from video.generation_scheduler import GenerationScheduler


class AutoVideoController(QObject):
    """把后台调度事件安全转发到 GUI 主线程。"""

    generation_requested = Signal(str)

    def __init__(self, logger: Logger | None = None, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self.logger = logger or logging.getLogger(__name__)
        self._scheduler = GenerationScheduler(self._on_schedule_due, self.logger)

    @property
    def is_running(self) -> bool:
        """返回每日自动调度是否已启动。"""
        return self._scheduler.is_running

    def start(
        self,
        mode: str = "daily",
        interval_seconds: int = 86400,
        daily_time: str = "00:00",
    ) -> bool:
        """按当前计划启动自动生成调度。"""
        return self._scheduler.start(mode, interval_seconds, daily_time)

    def stop(self) -> bool:
        """停止每日零点调度。"""
        return self._scheduler.stop()

    def _on_schedule_due(self, trigger_time: date | datetime) -> None:
        """在调度线程中发出信号，不直接调用 GUI 或视频线程对象。"""
        target_date = trigger_time.date() if isinstance(trigger_time, datetime) else trigger_time
        self.generation_requested.emit(target_date.isoformat())
