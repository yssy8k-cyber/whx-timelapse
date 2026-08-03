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

    def test_video_plan_fields_round_trip(self) -> None:
        with TemporaryDirectory() as directory:
            manager = ConfigManager(Path(directory) / "settings.json")
            expected = AppConfig(
                video_output_directory="D:/Timelapse/Videos",
                image_retention_policy="keep_recent_days",
                image_retention_days=14,
                video_filename_template="{camera}_{date}_{time}.mp4",
                video_overwrite_policy="prompt",
                schedule_mode="interval",
                schedule_interval_seconds=1800,
                generation_range="last_24_hours",
                auto_open_output_directory=True,
                show_completion_prompt=False,
            )

            self.assertTrue(manager.save(expected))
            self.assertEqual(manager.load(), expected)


if __name__ == "__main__":
    unittest.main()
