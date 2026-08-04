"""视频生成模块的独立测试。"""

from __future__ import annotations

import logging
import subprocess
import tempfile
import unittest
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Sequence

from video.ffmpeg_runner import FFmpegExecutionError
from video.ffmpeg_runner import FFmpegRunner
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
            self.assertIn("-start_number", runner.arguments)
            self.assertNotIn("-pattern_type", runner.arguments)
            self.assertTrue(any(argument.endswith("%08d.jpg") for argument in runner.arguments))
            self.assertTrue(list(image_directory.glob("*.jpg")))

    def test_reports_progress_while_staging_images(self) -> None:
        with tempfile.TemporaryDirectory() as temp_directory:
            image_directory = Path(temp_directory) / "2026-08-02"
            self._create_images(image_directory, 3)
            progress: list[tuple[int, int, str]] = []
            generator = VideoGenerator(VideoConfig(fps=25), logging.getLogger(__name__), FakeRunner())

            generator.generate(
                image_directory,
                progress_callback=lambda completed, total, message: progress.append(
                    (completed, total, message)
                ),
            )

            self.assertEqual([item[0] for item in progress[:3]], [1, 2, 3])
            self.assertEqual(progress[-1][2], "视频生成完成")

    def test_real_ffmpeg_generates_video_from_staged_sequence(self) -> None:
        """使用实际 FFmpeg 验证 Windows 兼容的 image2 序列参数。"""
        import cv2
        import numpy as np

        with tempfile.TemporaryDirectory() as temp_directory:
            image_directory = Path(temp_directory) / "2026-08-02"
            image_directory.mkdir(parents=True)
            for index in range(3):
                frame = np.full((48, 64, 3), index * 60, dtype=np.uint8)
                image_path = image_directory / f"20260802_08000{index}.jpg"
                self.assertTrue(cv2.imwrite(str(image_path), frame))
            output_path = Path(temp_directory) / "real.mp4"
            generator = VideoGenerator(
                VideoConfig(fps=15),
                logging.getLogger(__name__),
                FFmpegRunner(),
            )

            generated = generator.generate(image_directory, output_path)

            self.assertEqual(generated, output_path)
            self.assertGreater(output_path.stat().st_size, 0)

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

    def test_generates_multiple_date_directories_and_renames_collision(self) -> None:
        with tempfile.TemporaryDirectory() as temp_directory:
            root = Path(temp_directory) / "images"
            first = root / "2026-08-02"
            second = root / "2026-08-03"
            self._create_images(first, 2)
            self._create_images(second, 2)
            output = Path(temp_directory) / "videos" / "Timelapse.mp4"
            output.parent.mkdir()
            output.write_bytes(b"old")
            generator = VideoGenerator(
                VideoConfig(overwrite_policy="rename"),
                logging.getLogger(__name__),
                FakeRunner(),
            )

            generated = generator.generate_range([first, second], output)

            self.assertEqual(generated.name, "Timelapse_001.mp4")
            self.assertTrue(generated.exists())
            self.assertEqual(len(list(first.glob("*.jpg"))), 2)
            self.assertEqual(len(list(second.glob("*.jpg"))), 2)

    def test_keep_recent_days_removes_old_date_images_after_success(self) -> None:
        with tempfile.TemporaryDirectory() as temp_directory:
            root = Path(temp_directory) / "images"
            old_date = date.today() - timedelta(days=10)
            old_directory = root / old_date.isoformat()
            current_directory = root / date.today().isoformat()
            self._create_images(old_directory, 1)
            self._create_images(current_directory, 1)
            generator = VideoGenerator(
                VideoConfig(
                    image_retention_policy="keep_recent_days",
                    image_retention_days=3,
                    image_root_directory=root,
                ),
                logging.getLogger(__name__),
                FakeRunner(),
            )

            generator.generate(current_directory, Path(temp_directory) / "out.mp4")

            self.assertEqual(list(old_directory.glob("*.jpg")), [])
            self.assertTrue(list(current_directory.glob("*.jpg")))

    def test_recent_time_filter_uses_capture_filename_timestamp(self) -> None:
        with tempfile.TemporaryDirectory() as temp_directory:
            directory = Path(temp_directory) / "2026-08-03"
            directory.mkdir(parents=True)
            for name in (
                "20260803_100000.jpg",
                "20260803_120000.jpg",
                "20260803_140000.jpg",
            ):
                (directory / name).write_bytes(b"jpeg")
            generator = VideoGenerator(
                VideoConfig(
                    image_start_datetime=datetime(2026, 8, 3, 11, 0),
                    image_end_datetime=datetime(2026, 8, 3, 13, 0),
                ),
                logging.getLogger(__name__),
                FakeRunner(),
            )

            selected = generator._find_images_in_directories([directory])

            self.assertEqual([path.name for path in selected], ["20260803_120000.jpg"])


if __name__ == "__main__":
    unittest.main()
