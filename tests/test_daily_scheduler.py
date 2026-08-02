"""每日自动生成调度器测试。"""

from __future__ import annotations

import logging
import unittest
from datetime import date, datetime, timezone

from video.daily_scheduler import DailyVideoScheduler


class DailyVideoSchedulerTests(unittest.TestCase):
    def test_next_run_at_returns_next_local_midnight(self) -> None:
        now = datetime(2026, 8, 2, 13, 45, 10)
        self.assertEqual(
            DailyVideoScheduler.next_run_at(now),
            datetime(2026, 8, 3, 0, 0, 0),
        )

    def test_next_run_at_preserves_timezone(self) -> None:
        now = datetime(2026, 8, 2, 13, 45, tzinfo=timezone.utc)
        next_run = DailyVideoScheduler.next_run_at(now)
        self.assertEqual(next_run, datetime(2026, 8, 3, tzinfo=timezone.utc))

    def test_trigger_uses_previous_calendar_day(self) -> None:
        generated_dates: list[date] = []
        scheduler = DailyVideoScheduler(
            generated_dates.append,
            logging.getLogger(__name__),
        )

        self.assertTrue(scheduler.trigger_previous_day(datetime(2026, 8, 3, 0, 0)))
        self.assertEqual(generated_dates, [date(2026, 8, 2)])

    def test_callback_failure_is_captured(self) -> None:
        def failing_callback(_target_date: date) -> None:
            raise OSError("磁盘不可用")

        scheduler = DailyVideoScheduler(failing_callback, logging.getLogger(__name__))
        self.assertFalse(scheduler.trigger_previous_day(datetime(2026, 8, 3)))

    def test_scheduler_starts_and_stops_without_busy_loop(self) -> None:
        scheduler = DailyVideoScheduler(lambda _target_date: None, logging.getLogger(__name__))

        self.assertTrue(scheduler.start())
        self.assertFalse(scheduler.start())
        self.assertTrue(scheduler.stop())
        self.assertFalse(scheduler.is_running)


if __name__ == "__main__":
    unittest.main()
