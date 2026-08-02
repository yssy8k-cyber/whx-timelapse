"""RTSP 视频流的独立测试。"""

from __future__ import annotations

import logging
import unittest

import numpy as np

from camera.rtsp_stream import RTSPStream, RTSPStreamError


class FakeVideoCapture:
    """用于测试的最小 VideoCapture 替身。"""

    def __init__(self, url: str, opened: bool = True, readable: bool = True) -> None:
        self.url = url
        self.opened = opened
        self.readable = readable
        self.released = False
        self.frame = np.zeros((12, 16, 3), dtype=np.uint8)

    def set(self, _property_id: int, _value: float) -> bool:
        return True

    def isOpened(self) -> bool:
        return self.opened and not self.released

    def read(self) -> tuple[bool, np.ndarray | None]:
        if not self.isOpened() or not self.readable:
            return False, None
        return True, self.frame

    def release(self) -> None:
        self.released = True


class RTSPStreamTests(unittest.TestCase):
    def test_connect_read_copy_and_disconnect(self) -> None:
        captures: list[FakeVideoCapture] = []

        def factory(url: str) -> FakeVideoCapture:
            capture = FakeVideoCapture(url)
            captures.append(capture)
            return capture

        stream = RTSPStream(logging.getLogger(__name__), factory)
        stream.connect("rtsp://192.168.1.64:554/Streaming/Channels/101", "admin", "p@ss")

        frame = stream.read_frame()
        self.assertTrue(stream.is_connected)
        self.assertIsNotNone(frame)
        self.assertIsNot(frame, captures[0].frame)
        self.assertIn("admin:p%40ss@", captures[0].url)

        stream.disconnect()
        self.assertFalse(stream.is_connected)
        self.assertTrue(captures[0].released)

    def test_open_failure_raises_and_releases_capture(self) -> None:
        captures: list[FakeVideoCapture] = []

        def factory(url: str) -> FakeVideoCapture:
            capture = FakeVideoCapture(url, opened=False)
            captures.append(capture)
            return capture

        stream = RTSPStream(logging.getLogger(__name__), factory)
        with self.assertRaises(RTSPStreamError):
            stream.connect("rtsp://127.0.0.1/stream", "", "")
        self.assertTrue(captures[0].released)


if __name__ == "__main__":
    unittest.main()
