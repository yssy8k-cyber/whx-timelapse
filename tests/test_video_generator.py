"""视频生成模块的独立测试。"""

from __future__ import annotations

import logging
import subprocess
import tempfile
import unittest
from pathlib import Path
from typing import Sequence

from video.ffmpeg_runner import FFmpegExecutionError
from video.video_generator import VideoConfig, VideoGenerationError, VideoGenerator


class FakeRunner:
    """记录参数并模拟 FFmpeg 输出。"""

    def __init__(self, returncode: int = 0) -> None:
        self.returncode = returncode
        self.arguments: list[str] = []

    def run(self, arguments: Sequence[str]) -> subprocess.CompletedProcess[str]:
        self.arguments = list(arguments)
        output_path = Path(self.arguments[-1])
        if self.returncode == 0:
            output_path.write_bytes(b"fake mp4")
            return subprocess.CompletedProcess(self.arguments, 0, "", "")
        return subprocess.CompletedProcess(self.arguments, self.returncode, "", "ffmpeg error")


class VideoGeneratorTests(unittest.TestCase):
    def _create_images(self, directory: Path, count: int = 3) -> None:
        directory.mkdir(parents=True)
        for index in range(count):
            (directory / f"20260802_08000{index}.jpg").write_bytes(b"jpeg")

    def test_builds_h264_video_and_keeps_images_by_default(self) -> None:
        with tempfile.TemporaryDirectory() as temp_directory:
            image_directory = Path(temp_directory) / "2026-08-02"
            self._create_images(image_directory)
            runner = FakeRunner()
            generator = VideoGenerator(
                VideoConfig(fps=30),
                logging.getLogger(__name__),
                runner,
            )

            output_path = generator.generate(image_directory)

            self.assertEqual(output_path.name, "2026-08-02.mp4")
            self.assertTrue(output_path.exists())
            self.assertIn("-framerate", runner.arguments)
            self.assertIn("30", runner.arguments)
            self.assertIn("libx264", runner.arguments)
            self.assertTrue(list(image_directory.glob("*.jpg")))

    def test_deletes_images_only_after_success(self) -> None:
        with tempfile.TemporaryDirectory() as temp_directory:
            image_directory = Path(temp_directory) / "2026-08-02"
            self._create_images(image_directory)
            generator = VideoGenerator(
                VideoConfig(delete_images_after_video=True),
                logging.getLogger(__name__),
                FakeRunner(),
            )

            generator.generate(image_directory)

            self.assertEqual(list(image_directory.glob("*.jpg")), [])

    def test_ffmpeg_failure_keeps_images(self) -> None:
        with tempfile.TemporaryDirectory() as temp_directory:
            image_directory = Path(temp_directory) / "2026-08-02"
            self._create_images(image_directory)
            generator = VideoGenerator(
                VideoConfig(delete_images_after_video=True),
                logging.getLogger(__name__),
                FakeRunner(returncode=1),
            )

            with self.assertRaises(FFmpegExecutionError):
                generator.generate(image_directory)

            self.assertEqual(len(list(image_directory.glob("*.jpg"))), 3)

    def test_empty_directory_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temp_directory:
            with self.assertRaises(VideoGenerationError):
                VideoGenerator(VideoConfig(15)).generate(Path(temp_directory))


if __name__ == "__main__":
    unittest.main()
