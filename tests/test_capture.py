"""定时截图模块的独立测试。"""

from __future__ import annotations

import logging
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from threading import Event

import cv2
import numpy as np

from capture.capture_worker import CaptureConfig, CaptureWorker
from capture.image_storage import ImageStorage


class ImageStorageTests(unittest.TestCase):
    """测试日期目录、文件名和 JPEG 写入。"""

    def test_save_frame_uses_date_directory_and_timestamp_name(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            storage = ImageStorage(Path(directory), 90, logging.getLogger(__name__))
            frame = np.zeros((20, 30, 3), dtype=np.uint8)
            captured_at = datetime(2026, 8, 2, 8, 0, 0)

            image_path = storage.save_frame(frame, captured_at)

            self.assertEqual(
                image_path,
                Path(directory) / "2026-08-02" / "20260802_080000.jpg",
            )
            self.assertIsNotNone(cv2.imread(str(image_path)))

    def test_save_frame_does_not_overwrite_same_second(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            storage = ImageStorage(Path(directory), 90, logging.getLogger(__name__))
            frame = np.zeros((20, 30, 3), dtype=np.uint8)
            captured_at = datetime(2026, 8, 2, 8, 0, 0)

            first = storage.save_frame(frame, captured_at)
            second = storage.save_frame(frame, captured_at)

            self.assertEqual(first.name, "20260802_080000.jpg")
            self.assertEqual(second.name, "20260802_080000_001.jpg")
            self.assertEqual(len(list(first.parent.glob("*.jpg"))), 2)


class CaptureWorkerTests(unittest.TestCase):
    """测试线程启动、截图成功和安全停止。"""

    def test_worker_captures_a_frame_and_stops(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            captured = Event()
            frame = np.zeros((20, 30, 3), dtype=np.uint8)

            worker = CaptureWorker(
                frame_provider=lambda: frame,
                config=CaptureConfig(0.1, 85, Path(directory)),
                logger=logging.getLogger(__name__),
                on_success=lambda _path: captured.set(),
            )

            self.assertTrue(worker.start())
            self.assertTrue(captured.wait(2.0))
            self.assertTrue(worker.stop())
            self.assertFalse(worker.is_running)
            self.assertTrue(list(Path(directory).rglob("*.jpg")))

    def test_capture_failure_does_not_kill_worker_before_stop(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            failed = Event()
            worker = CaptureWorker(
                frame_provider=lambda: None,
                config=CaptureConfig(0.1, 85, Path(directory)),
                logger=logging.getLogger(__name__),
                on_failure=lambda _error: failed.set(),
            )

            self.assertTrue(worker.start())
            self.assertTrue(failed.wait(2.0))
            self.assertTrue(worker.is_running)
            self.assertTrue(worker.stop())


if __name__ == "__main__":
    unittest.main()
