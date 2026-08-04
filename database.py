"""SQLite 持久化层：设备、软件配置和视频任务记录。"""

from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable, Iterator


class SQLiteDatabase:
    """为桌面客户端提供轻量、可迁移的本地数据库。"""

    def __init__(self, path: Path) -> None:
        self.path = Path(path)

    def initialize(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS cameras (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    rtsp_url TEXT NOT NULL DEFAULT '',
                    username TEXT NOT NULL DEFAULT '',
                    password TEXT NOT NULL DEFAULT '',
                    updated_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS app_config (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS video_tasks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    camera_name TEXT NOT NULL,
                    image_directory TEXT NOT NULL,
                    output_path TEXT NOT NULL,
                    image_count INTEGER NOT NULL DEFAULT 0,
                    status TEXT NOT NULL,
                    error_message TEXT NOT NULL DEFAULT '',
                    started_at TEXT NOT NULL,
                    finished_at TEXT NOT NULL DEFAULT ''
                );
                """
            )

    def replace_cameras(self, devices: Iterable[Any]) -> None:
        """同步摄像头档案；调用方传入带有配置属性的设备对象。"""
        now = datetime.now().isoformat(timespec="seconds")
        rows = [
            (
                str(device.name),
                str(device.rtsp_url),
                str(device.username),
                str(device.password),
                now,
            )
            for device in devices
        ]
        with self._connect() as connection:
            connection.execute("DELETE FROM cameras")
            connection.executemany(
                "INSERT INTO cameras(name, rtsp_url, username, password, updated_at) VALUES (?, ?, ?, ?, ?)",
                rows,
            )

    def save_app_config(self, values: dict[str, Any]) -> None:
        rows = [(key, json.dumps(value, ensure_ascii=False)) for key, value in values.items()]
        with self._connect() as connection:
            connection.executemany(
                "INSERT INTO app_config(key, value) VALUES (?, ?) "
                "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                rows,
            )

    def create_video_task(
        self,
        camera_name: str,
        image_directory: Path,
        output_path: Path,
        image_count: int,
    ) -> int:
        started_at = datetime.now().isoformat(timespec="seconds")
        with self._connect() as connection:
            cursor = connection.execute(
                "INSERT INTO video_tasks(camera_name, image_directory, output_path, image_count, status, started_at) "
                "VALUES (?, ?, ?, ?, 'running', ?)",
                (camera_name, str(image_directory), str(output_path), image_count, started_at),
            )
            return int(cursor.lastrowid)

    def finish_video_task(self, task_id: int, status: str, error_message: str = "") -> None:
        if status not in {"completed", "failed"}:
            raise ValueError("视频任务状态无效")
        with self._connect() as connection:
            connection.execute(
                "UPDATE video_tasks SET status=?, error_message=?, finished_at=? WHERE id=?",
                (status, error_message, datetime.now().isoformat(timespec="seconds"), task_id),
            )

    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        connection = sqlite3.connect(self.path)
        try:
            connection.execute("PRAGMA journal_mode=WAL")
            yield connection
        except Exception:
            connection.rollback()
            raise
        else:
            connection.commit()
        finally:
            connection.close()


__all__ = ["SQLiteDatabase"]
