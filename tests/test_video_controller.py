"""视频生成 Qt 控制器测试。"""

from __future__ import annotations

import logging
import tempfile
import unittest
from pathlib import Path

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication

from ui.video_controller import VideoController
from video.video_generator import VideoConfig


class FakeVideoGenerator:
    """模拟生成成功的视频服务。"""

    def __init__(self, config: VideoConfig, _logger: logging.Logger) -> None:
        self.config = config

    def generate(self, image_directory: Path) -> Path:
        output_path = image_directory.parent / f"{image_directory.name}.mp4"
        output_path.write_bytes(b"fake video")
        return output_path


class FailingVideoGenerator(FakeVideoGenerator):
    """模拟 FFmpeg 失败的视频服务。"""

    def generate(self, _image_directory: Path) -> Path:
        raise RuntimeError("模拟 FFmpeg 失败")


class VideoControllerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.app = QApplication.instance() or QApplication([])

    def test_generation_runs_async_and_emits_success(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            controller = VideoController(
                logging.getLogger(__name__),
                generator_factory=lambda config, logger: FakeVideoGenerator(config, logger),
            )
            results: list[str] = []
            controller.generated.connect(lambda path: results.append(path))
            image_directory = Path(directory) / "2026-08-02"

            self.assertTrue(controller.start(image_directory, 24, False))
            self.assertFalse(controller.start(image_directory, 24, False))
            QTimer.singleShot(1000, self.app.quit)
            self.app.exec()

            self.assertEqual(len(results), 1)
            self.assertFalse(controller.is_running)
            self.assertTrue(Path(results[0]).exists())
            controller.shutdown()

    def test_generation_failure_emits_failure_and_releases_state(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            controller = VideoController(
                logging.getLogger(__name__),
                generator_factory=lambda config, logger: FailingVideoGenerator(config, logger),
            )
            errors: list[str] = []
            controller.failed.connect(lambda message: errors.append(message))

            self.assertTrue(controller.start(Path(directory), 15, False))
            QTimer.singleShot(1000, self.app.quit)
            self.app.exec()

            self.assertEqual(errors, ["模拟 FFmpeg 失败"])
            self.assertFalse(controller.is_running)
            controller.shutdown()


if __name__ == "__main__":
    unittest.main()
