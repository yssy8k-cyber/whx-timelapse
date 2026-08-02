"""多设备配置和旧版 JSON 迁移测试。"""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from config.config_manager import AppConfig, ConfigManager
from config.device_config import DeviceConfig


class DeviceConfigTests(unittest.TestCase):
    def test_legacy_single_device_fields_are_migrated(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "settings.json"
            path.write_text(
                json.dumps(
                    {
                        "rtsp_url": "rtsp://camera/stream",
                        "username": "admin",
                        "password": "secret",
                    }
                ),
                encoding="utf-8",
            )

            config = ConfigManager(path).load()

            self.assertEqual(len(config.devices), 1)
            self.assertEqual(config.devices[0].name, "海康威视摄像头 1")
            self.assertEqual(config.devices[0].rtsp_url, "rtsp://camera/stream")

    def test_multiple_devices_round_trip_and_active_device_sync(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            config = AppConfig(
                devices=[
                    DeviceConfig("入口摄像头", "rtsp://entry/stream"),
                    DeviceConfig("仓库摄像头", "rtsp://warehouse/stream", "admin", "secret"),
                ],
                active_device_index=1,
            )
            manager = ConfigManager(Path(directory) / "settings.json")

            self.assertTrue(manager.save(config))
            loaded = manager.load()

            self.assertEqual(loaded.devices, config.devices)
            self.assertEqual(loaded.active_device_index, 1)
            self.assertEqual(loaded.rtsp_url, "rtsp://warehouse/stream")


if __name__ == "__main__":
    unittest.main()
