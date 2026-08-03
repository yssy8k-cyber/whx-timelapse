"""FFmpeg 调用器的错误信息测试。"""

from __future__ import annotations

import subprocess
import unittest
from unittest.mock import patch

from video.ffmpeg_runner import FFmpegExecutionError, FFmpegRunner


class FFmpegRunnerTests(unittest.TestCase):
    """验证 FFmpeg 的诊断信息不会被吞掉。"""

    @patch("video.ffmpeg_runner.subprocess.run")
    def test_uses_stdout_when_stderr_is_empty(self, run_mock) -> None:
        run_mock.return_value = subprocess.CompletedProcess(
            ["ffmpeg"],
            1,
            "输入图片序列无效",
            "",
        )

        with self.assertRaisesRegex(FFmpegExecutionError, "输入图片序列无效"):
            FFmpegRunner("ffmpeg").run(["-i", "input"])

    @patch("video.ffmpeg_runner.subprocess.run")
    def test_includes_exit_code_and_command_when_outputs_are_empty(
        self,
        run_mock,
    ) -> None:
        run_mock.return_value = subprocess.CompletedProcess(
            ["ffmpeg"],
            3221225781,
            "",
            "",
        )

        with self.assertRaisesRegex(
            FFmpegExecutionError,
            "退出码: 3221225781",
        ) as context:
            FFmpegRunner("ffmpeg").run(["-i", "C:/Timelapse Images/%08d.jpg"])

        self.assertIn("C:/Timelapse Images/%08d.jpg", str(context.exception))
        self.assertIn("请检查图片目录", str(context.exception))


if __name__ == "__main__":
    unittest.main()
