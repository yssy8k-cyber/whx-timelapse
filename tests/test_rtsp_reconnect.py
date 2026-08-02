"""RTSP 自动重连管理器测试。"""

from __future__ import annotations

import logging
import time
import unittest
from threading import Event

import numpy as np

from camera.rtsp_reconnect import RTSPReconnectManager


class FakeStream:
    """支持模拟断流和重连失败的流对象。"""

    def __init__(self) -> None:
        self.connect_calls = 0
        self.fail_next_connects = 0
        self.fail_next_read = False
        self.connected = False
        self.reconnected = Event()
        self.frame = np.zeros((8, 8, 3), dtype=np.uint8)

    def connect(self, _url: str, _username: str, _password: str) -> None:
        self.connect_calls += 1
        if self.fail_next_connects > 0:
            self.fail_next_connects -= 1
            raise OSError("模拟网络异常")
        self.connected = True
        if self.connect_calls > 1:
            self.reconnected.set()

    def read_frame(self) -> np.ndarray | None:
        if self.fail_next_read:
            self.fail_next_read = False
            self.connected = False
            return None
        return self.frame if self.connected else None

    def disconnect(self) -> None:
        self.connected = False


class RTSPReconnectManagerTests(unittest.TestCase):
    def test_disconnect_starts_reconnect_after_empty_frame(self) -> None:
        stream = FakeStream()
        manager = RTSPReconnectManager(stream, logging.getLogger(__name__), 0.01)
        manager.connect("rtsp://camera/stream", "admin", "password")
        stream.fail_next_read = True

        self.assertIsNone(manager.read_frame())
        self.assertTrue(stream.reconnected.wait(1.0))
        self.assertIsNotNone(manager.read_frame())
        manager.disconnect()

    def test_failed_reconnect_is_retried(self) -> None:
        stream = FakeStream()
        manager = RTSPReconnectManager(stream, logging.getLogger(__name__), 0.01)
        manager.connect("rtsp://camera/stream", "admin", "password")
        stream.fail_next_read = True
        stream.fail_next_connects = 1

        manager.read_frame()
        self.assertTrue(stream.reconnected.wait(1.0))
        self.assertGreaterEqual(stream.connect_calls, 3)
        manager.disconnect()

    def test_disconnect_interrupts_reconnect_wait(self) -> None:
        stream = FakeStream()
        manager = RTSPReconnectManager(stream, logging.getLogger(__name__), 10.0)
        manager.connect("rtsp://camera/stream", "admin", "password")
        stream.fail_next_read = True
        manager.read_frame()

        started = time.monotonic()
        manager.disconnect()

        self.assertLess(time.monotonic() - started, 1.0)
        self.assertFalse(stream.connected)


if __name__ == "__main__":
    unittest.main()
