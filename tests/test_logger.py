"""异步日志运行时测试。"""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from log.logger import configure_logging, shutdown_logging


class LoggerTests(unittest.TestCase):
    def test_log_is_written_and_runtime_can_shutdown(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            log_directory = Path(directory)
            logger = configure_logging(log_directory)
            logger.info("异步日志测试消息")
            shutdown_logging(logger)

            log_file = log_directory / "timelapse_studio.log"
            self.assertTrue(log_file.exists())
            self.assertIn("异步日志测试消息", log_file.read_text(encoding="utf-8"))

    def test_logger_can_be_configured_again_after_shutdown(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            logger = configure_logging(Path(directory))
            shutdown_logging(logger)
            logger = configure_logging(Path(directory))
            logger.info("重新初始化日志")
            shutdown_logging(logger)
            self.assertTrue((Path(directory) / "timelapse_studio.log").exists())


if __name__ == "__main__":
    unittest.main()
