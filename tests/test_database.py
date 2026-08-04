"""SQLite 数据库持久化测试。"""

from __future__ import annotations

import sqlite3
import tempfile
import unittest
from dataclasses import dataclass
from pathlib import Path

from database import SQLiteDatabase


@dataclass
class Device:
    name: str = "Camera 01"
    rtsp_url: str = "rtsp://192.168.1.64:554/Streaming/Channels/101"
    username: str = "admin"
    password: str = "secret"


class DatabaseTests(unittest.TestCase):
    def test_persists_devices_settings_and_video_task(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            database = SQLiteDatabase(Path(directory) / "config" / "timelapse.db")
            database.initialize()
            database.replace_cameras([Device()])
            database.save_app_config({"capture_interval": 10, "dark_mode": True})
            task_id = database.create_video_task("Camera 01", Path("images/2026-08-04"), Path("videos/2026-08-04.mp4"), 10000)
            database.finish_video_task(task_id, "completed")

            with sqlite3.connect(database.path) as connection:
                self.assertEqual(connection.execute("SELECT COUNT(*) FROM cameras").fetchone()[0], 1)
                self.assertEqual(connection.execute("SELECT COUNT(*) FROM app_config").fetchone()[0], 2)
                self.assertEqual(connection.execute("SELECT status FROM video_tasks WHERE id=?", (task_id,)).fetchone()[0], "completed")


if __name__ == "__main__":
    unittest.main()
