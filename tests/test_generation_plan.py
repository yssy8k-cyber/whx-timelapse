"""视频生成范围和文件名计划测试。"""

from __future__ import annotations

import unittest
from datetime import date, datetime
from pathlib import Path

from video.generation_plan import (
    DateRange,
    image_directories,
    render_filename,
    resolve_date_range,
)


class GenerationPlanTests(unittest.TestCase):
    def test_resolves_recent_ranges(self) -> None:
        now = datetime(2026, 8, 3, 18, 30)
        self.assertEqual(
            resolve_date_range("yesterday", now).start,
            date(2026, 8, 2),
        )
        last_seven = resolve_date_range("last_7_days", now)
        self.assertEqual(last_seven.start, date(2026, 7, 28))
        self.assertEqual(last_seven.end, date(2026, 8, 3))
        last_day = resolve_date_range("last_24_hours", now)
        self.assertEqual(last_day.start_datetime, datetime(2026, 8, 2, 18, 30))
        self.assertEqual(last_day.end_datetime, now)

    def test_custom_range_and_directories(self) -> None:
        date_range = resolve_date_range(
            "custom",
            custom_start=date(2026, 8, 1),
            custom_end=date(2026, 8, 3),
        )
        self.assertEqual(
            image_directories(Path("D:/Images"), date_range),
            [
                Path("D:/Images/2026-08-01"),
                Path("D:/Images/2026-08-02"),
                Path("D:/Images/2026-08-03"),
            ],
        )

    def test_renders_safe_template(self) -> None:
        date_range = DateRange(date(2026, 8, 3), date(2026, 8, 3))
        filename = render_filename(
            "{camera}:{date}:{time}",
            "入口/摄像头",
            date_range,
            datetime(2026, 8, 3, 8, 5, 4),
        )
        self.assertEqual(filename, "入口_摄像头_2026-08-03_080504.mp4")


if __name__ == "__main__":
    unittest.main()
