"""配置模块的基础测试。"""

from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from config.config_manager import AppConfig, ConfigManager


class ConfigManagerTests(unittest.TestCase):
    def test_save_and_load_round_trip(self) -> None:
        with TemporaryDirectory() as directory:
            path = Path(directory) / "settings.json"
            manager = ConfigManager(path)
            expected = AppConfig(
                rtsp_url="rtsp://127.0.0.1:554/Streaming/Channels/101",
                username="admin",
                password="password",
                save_directory="D:/Timelapse",
                jpeg_quality=88,
                video_fps=30,
                delete_images_after_video=True,
                auto_generate_video=True,
                dark_mode=True,
            )

            self.assertTrue(manager.save(expected))
            self.assertEqual(manager.load(), expected)


if __name__ == "__main__":
    unittest.main()
