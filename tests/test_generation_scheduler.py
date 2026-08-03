"""通用视频生成计划调度器测试。"""

from __future__ import annotations

import logging
import unittest
from datetime import datetime

from video.generation_scheduler import GenerationScheduler


class GenerationSchedulerTests(unittest.TestCase):
    def test_next_interval_run(self) -> None:
        now = datetime(2026, 8, 3, 10, 0)
        self.assertEqual(
            GenerationScheduler.next_run_at(now, "interval", 1800, "00:00"),
            datetime(2026, 8, 3, 10, 30),
        )

    def test_next_daily_run_rolls_to_tomorrow(self) -> None:
        now = datetime(2026, 8, 3, 18, 0)
        self.assertEqual(
            GenerationScheduler.next_run_at(now, "daily", 1800, "08:00"),
            datetime(2026, 8, 4, 8, 0),
        )

    def test_invalid_daily_time_is_rejected(self) -> None:
        scheduler = GenerationScheduler(lambda _now: None, logging.getLogger(__name__))
        with self.assertRaises(ValueError):
            scheduler.start("daily", 1800, "25:00")


if __name__ == "__main__":
    unittest.main()
