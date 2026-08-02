"""自动视频控制器测试。"""

from __future__ import annotations

import logging
import unittest
from datetime import date

from PySide6.QtWidgets import QApplication

from ui.auto_video_controller import AutoVideoController


class AutoVideoControllerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.app = QApplication.instance() or QApplication([])

    def test_scheduler_event_is_forwarded_as_qt_signal(self) -> None:
        controller = AutoVideoController(logging.getLogger(__name__))
        requested_dates: list[str] = []
        controller.generation_requested.connect(requested_dates.append)

        controller._on_schedule_due(date(2026, 8, 2))

        self.assertEqual(requested_dates, ["2026-08-02"])
        controller.stop()

    def test_controller_starts_and_stops_scheduler(self) -> None:
        controller = AutoVideoController(logging.getLogger(__name__))

        self.assertTrue(controller.start())
        self.assertFalse(controller.start())
        self.assertTrue(controller.stop())
        self.assertFalse(controller.is_running)


if __name__ == "__main__":
    unittest.main()
