"""每日零点自动触发视频生成。"""

from __future__ import annotations

import logging
from datetime import date, datetime, time, timedelta
from logging import Logger
from threading import Event, Lock, Thread, current_thread
from typing import Callable


DateGenerationCallback = Callable[[date], None]
NowProvider = Callable[[], datetime]


class DailyVideoScheduler:
    """按本地时间每天零点触发上一自然日的视频生成。"""

    def __init__(
        self,
        on_generate: DateGenerationCallback,
        logger: Logger | None = None,
        now_provider: NowProvider | None = None,
    ) -> None:
        self.on_generate = on_generate
        self.logger = logger or logging.getLogger(__name__)
        self._now_provider = now_provider or datetime.now
        self._stop_event = Event()
        self._state_lock = Lock()
        self._thread: Thread | None = None

    @property
    def is_running(self) -> bool:
        """返回自动调度线程是否正在运行。"""
        with self._state_lock:
            return self._thread is not None and self._thread.is_alive()

    @staticmethod
    def next_run_at(now: datetime) -> datetime:
        """计算本地时间的下一个零点，保留时区信息。"""
        tomorrow = now.date() + timedelta(days=1)
        return datetime.combine(tomorrow, time.min, tzinfo=now.tzinfo)

    @staticmethod
    def target_date_at_midnight(now: datetime) -> date:
        """计算零点触发时应该生成的上一自然日。"""
        return now.date() - timedelta(days=1)

    def start(self) -> bool:
        """启动每日调度线程；已经运行时返回 False。"""
        with self._state_lock:
            if self._thread is not None and self._thread.is_alive():
                return False
            self._stop_event.clear()
            self._thread = Thread(
                target=self._run,
                name="timelapse-daily-scheduler",
                daemon=True,
            )
            self._thread.start()
        self.logger.info("每日自动生成调度已启动")
        return True

    def stop(self, timeout: float = 5.0) -> bool:
        """停止调度线程并等待退出。"""
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
            self.logger.info("每日自动生成调度已停止")
        else:
            self.logger.warning("每日自动生成调度停止超时")
        return stopped

    def trigger_previous_day(self, now: datetime | None = None) -> bool:
        """立即触发一次上一自然日生成，便于手动执行和测试。"""
        current_time = now or self._now_provider()
        target_date = self.target_date_at_midnight(current_time)
        self.logger.info("自动生成触发: %s", target_date)
        try:
            self.on_generate(target_date)
        except Exception as error:  # 生成服务异常不能终止每日调度
            self.logger.exception("自动生成失败: %s", error)
            return False
        return True

    def _run(self) -> None:
        while not self._stop_event.is_set():
            now = self._now_provider()
            next_run = self.next_run_at(now)
            wait_seconds = max(0.0, (next_run - now).total_seconds())
            self.logger.info("下一次自动生成时间: %s", next_run)
            if self._stop_event.wait(wait_seconds):
                return
            if self._stop_event.is_set():
                return
            self.trigger_previous_day(self._now_provider())
