"""灵活的视频生成计划调度器。"""

from __future__ import annotations

import logging
from datetime import datetime, time, timedelta
from logging import Logger
from threading import Event, Lock, Thread, current_thread
from typing import Callable


ScheduleCallback = Callable[[datetime], None]


class GenerationScheduler:
    """支持固定间隔和每天固定时间的后台调度线程。"""

    def __init__(
        self,
        on_due: ScheduleCallback,
        logger: Logger | None = None,
        now_provider: Callable[[], datetime] | None = None,
    ) -> None:
        self.on_due = on_due
        self.logger = logger or logging.getLogger(__name__)
        self.now_provider = now_provider or datetime.now
        self._stop_event = Event()
        self._state_lock = Lock()
        self._thread: Thread | None = None
        self._mode = "manual"
        self._interval_seconds = 86400
        self._daily_time = "00:00"

    @property
    def is_running(self) -> bool:
        """返回调度线程是否正在运行。"""
        with self._state_lock:
            return self._thread is not None and self._thread.is_alive()

    def start(self, mode: str, interval_seconds: int, daily_time: str) -> bool:
        """按计划模式启动调度，手动模式不会创建线程。"""
        if self.is_running:
            return False
        if mode == "manual":
            self.stop()
            return False
        if mode not in {"interval", "daily"}:
            raise ValueError("自动生成计划模式无效")
        if interval_seconds < 60:
            raise ValueError("自动生成间隔不能小于 1 分钟")
        _parse_daily_time(daily_time)
        self.stop()
        with self._state_lock:
            self._mode = mode
            self._interval_seconds = interval_seconds
            self._daily_time = daily_time
            self._stop_event.clear()
            self._thread = Thread(
                target=self._run,
                name="timelapse-generation-scheduler",
                daemon=True,
            )
            self._thread.start()
        self.logger.info("视频生成计划已启动: %s", self.describe())
        return True

    def stop(self, timeout: float = 5.0) -> bool:
        """停止计划线程。"""
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
            self.logger.info("视频生成计划已停止")
        else:
            self.logger.warning("视频生成计划停止超时")
        return stopped

    def describe(self) -> str:
        """返回用于日志的计划描述。"""
        if self._mode == "interval":
            return f"每隔 {self._interval_seconds} 秒"
        return f"每天 {self._daily_time}"

    @staticmethod
    def next_run_at(
        now: datetime,
        mode: str,
        interval_seconds: int,
        daily_time: str,
    ) -> datetime:
        """计算计划下一次执行时间。"""
        if mode == "interval":
            return now + timedelta(seconds=interval_seconds)
        if mode != "daily":
            raise ValueError("手动模式没有下一次自动执行时间")
        scheduled_time = _parse_daily_time(daily_time)
        candidate = datetime.combine(now.date(), scheduled_time, tzinfo=now.tzinfo)
        if candidate <= now:
            candidate += timedelta(days=1)
        return candidate

    def _run(self) -> None:
        while not self._stop_event.is_set():
            now = self.now_provider()
            next_run = self.next_run_at(
                now,
                self._mode,
                self._interval_seconds,
                self._daily_time,
            )
            self.logger.info("下一次视频生成时间: %s", next_run)
            if self._stop_event.wait(max(0.0, (next_run - now).total_seconds())):
                return
            if self._stop_event.is_set():
                return
            trigger_time = self.now_provider()
            try:
                self.on_due(trigger_time)
            except Exception as error:
                self.logger.exception("视频生成计划回调失败: %s", error)


def _parse_daily_time(value: str) -> time:
    try:
        hour_text, minute_text = value.split(":", 1)
        result = time(int(hour_text), int(minute_text))
    except (ValueError, AttributeError):
        raise ValueError("每天固定时间必须是 HH:MM 格式") from None
    return result


__all__ = ["GenerationScheduler"]
