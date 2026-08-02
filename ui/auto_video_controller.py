"""每日自动生成调度器的 Qt 信号桥接层。"""

from __future__ import annotations

from datetime import date
import logging
from logging import Logger

from PySide6.QtCore import QObject, Signal

from video.daily_scheduler import DailyVideoScheduler


class AutoVideoController(QObject):
    """把后台调度事件安全转发到 GUI 主线程。"""

    generation_requested = Signal(str)

    def __init__(self, logger: Logger | None = None, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self.logger = logger or logging.getLogger(__name__)
        self._scheduler = DailyVideoScheduler(self._on_schedule_due, self.logger)

    @property
    def is_running(self) -> bool:
        """返回每日自动调度是否已启动。"""
        return self._scheduler.is_running

    def start(self) -> bool:
        """启动每日零点调度。"""
        return self._scheduler.start()

    def stop(self) -> bool:
        """停止每日零点调度。"""
        return self._scheduler.stop()

    def _on_schedule_due(self, target_date: date) -> None:
        """在调度线程中发出信号，不直接调用 GUI 或视频线程对象。"""
        self.generation_requested.emit(target_date.isoformat())
