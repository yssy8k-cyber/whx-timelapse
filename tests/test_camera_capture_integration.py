"""摄像头取帧接口与截图线程的连接测试。"""

from __future__ import annotations

import logging
import tempfile
import unittest
from pathlib import Path
from threading import Event

from camera.rtsp_stream import RTSPStream
from capture.capture_worker import CaptureConfig, CaptureWorker

from tests.test_rtsp_stream import FakeVideoCapture


class CameraCaptureIntegrationTests(unittest.TestCase):
    def test_capture_worker_reads_from_rtsp_stream(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            stream = RTSPStream(
                logging.getLogger(__name__),
                lambda url: FakeVideoCapture(url),
            )
            stream.connect("rtsp://127.0.0.1/stream", "", "")
            captured = Event()
            worker = CaptureWorker(
                frame_provider=stream.read_frame,
                config=CaptureConfig(0.1, 90, Path(directory)),
                logger=logging.getLogger(__name__),
                on_success=lambda _path: captured.set(),
            )

            self.assertTrue(worker.start())
            self.assertTrue(captured.wait(2.0))
            self.assertTrue(worker.stop())
            stream.disconnect()
            self.assertTrue(list(Path(directory).rglob("*.jpg")))


if __name__ == "__main__":
    unittest.main()
