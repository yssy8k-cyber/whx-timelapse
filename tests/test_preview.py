"""实时预览线程和状态工具测试。"""

from __future__ import annotations

import logging
import threading
import unittest

import numpy as np
from PySide6.QtWidgets import QApplication

from camera.preview_controller import PreviewWorker, stream_type_from_url


class FakePreviewStream:
    """提供连续彩色帧的独立预览流替身。"""

    def __init__(self) -> None:
        self.connected = False
        self.released = False
        self.frame = np.zeros((1080, 1920, 3), dtype=np.uint8)

    def connect(self, _url: str, _username: str, _password: str) -> None:
        self.connected = True

    def read_frame(self) -> np.ndarray | None:
        if not self.connected or self.released:
            return None
        return self.frame.copy()

    def disconnect(self) -> None:
        self.connected = False
        self.released = True


class PreviewWorkerTests(unittest.TestCase):
    """验证预览线程的帧转换和资源释放。"""

    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QApplication.instance() or QApplication([])

    def test_worker_emits_frames_at_limited_rate_and_releases_stream(self) -> None:
        stream = FakePreviewStream()
        connected = threading.Event()
        frame_received = threading.Event()
        finished = threading.Event()
        frames: list[tuple[int, int, float]] = []

        worker = PreviewWorker(
            "rtsp://127.0.0.1/Streaming/Channels/101",
            "admin",
            "password",
            logging.getLogger(__name__),
            lambda image, width, height, fps: (
                frames.append((image.width(), image.height(), fps)),
                frame_received.set(),
            ),
            connected.set,
            lambda _message: self.fail("预览不应失败"),
            finished.set,
            target_fps=10.0,
            stream_factory=lambda _logger: stream,
        )
        thread = threading.Thread(target=worker.run, daemon=True)
        thread.start()

        self.assertTrue(connected.wait(1.0))
        self.assertTrue(frame_received.wait(1.0))
        worker.stop()
        thread.join(2.0)

        self.assertFalse(thread.is_alive())
        self.assertTrue(finished.is_set())
        self.assertTrue(stream.released)
        self.assertEqual(frames[0][:2], (1920, 1080))
        self.assertLessEqual(frames[0][2], 10.0)

    def test_preview_fps_range_and_stream_type(self) -> None:
        with self.assertRaises(ValueError):
            PreviewWorker(
                "rtsp://camera/stream",
                "",
                "",
                logging.getLogger(__name__),
                lambda *_args: None,
                lambda: None,
                lambda _message: None,
                lambda: None,
                target_fps=16.0,
            )

        self.assertEqual(stream_type_from_url("rtsp://camera/101"), "主码流")
        self.assertEqual(stream_type_from_url("rtsp://camera/102"), "子码流")
        self.assertEqual(stream_type_from_url("rtsp://camera/live"), "未知码流")

    def test_preview_widget_uses_sixteen_by_nine_hint(self) -> None:
        from ui.preview_panel import VideoPreviewWidget

        widget = VideoPreviewWidget()
        self.assertTrue(widget.hasHeightForWidth())
        self.assertEqual(widget.heightForWidth(640), 360)


if __name__ == "__main__":
    unittest.main()
