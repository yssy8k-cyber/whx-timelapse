"""JSON 配置读写。"""

from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass, field, fields
from pathlib import Path
from typing import Any

from .device_config import DeviceConfig


@dataclass
class AppConfig:
    """应用当前配置和多设备配置档案。"""

    rtsp_url: str = ""
    username: str = ""
    password: str = ""
    save_directory: str = r"D:\Timelapse"
    video_output_directory: str = r"D:\Timelapse\Videos"
    capture_interval: int = 60
    jpeg_quality: int = 95
    video_fps: int = 24
    image_retention_policy: str = "keep_all"
    image_retention_days: int = 7
    video_filename_template: str = "Timelapse_{date}.mp4"
    video_overwrite_policy: str = "rename"
    schedule_mode: str = "manual"
    schedule_interval_seconds: int = 86400
    schedule_daily_time: str = "00:00"
    generation_range: str = "today"
    custom_range_start: str = ""
    custom_range_end: str = ""
    auto_open_output_directory: bool = False
    show_completion_prompt: bool = True
    log_video_generation: bool = True
    delete_images_after_video: bool = False
    auto_generate_video: bool = False
    dark_mode: bool = False
    devices: list[DeviceConfig] = field(default_factory=lambda: [DeviceConfig()])
    active_device_index: int = 0

    def sync_legacy_fields(self) -> None:
        """同步旧版字段并规范化视频计划配置。"""
        if not self.devices:
            self.devices.append(DeviceConfig())
        self.active_device_index = max(0, min(self.active_device_index, len(self.devices) - 1))
        active_device = self.devices[self.active_device_index]
        self.rtsp_url = active_device.rtsp_url
        self.username = active_device.username
        self.password = active_device.password
        if self.delete_images_after_video and self.image_retention_policy == "keep_all":
            self.image_retention_policy = "delete_after_video"
        if self.image_retention_policy not in {
            "keep_all",
            "delete_after_video",
            "keep_recent_days",
        }:
            self.image_retention_policy = "keep_all"
        self.image_retention_days = max(1, int(self.image_retention_days))
        self.delete_images_after_video = self.image_retention_policy == "delete_after_video"
        if self.video_overwrite_policy not in {"overwrite", "rename", "prompt"}:
            self.video_overwrite_policy = "rename"
        if self.schedule_mode not in {"interval", "daily", "manual"}:
            self.schedule_mode = "manual"
        self.schedule_interval_seconds = max(60, int(self.schedule_interval_seconds))
        if len(self.schedule_daily_time) != 5 or self.schedule_daily_time[2] != ":":
            self.schedule_daily_time = "00:00"
        if self.generation_range not in {
            "today",
            "yesterday",
            "last_24_hours",
            "last_7_days",
            "custom",
        }:
            self.generation_range = "today"
        self.video_filename_template = (
            self.video_filename_template.strip() or "Timelapse_{date}.mp4"
        )
        if self.auto_generate_video and self.schedule_mode == "manual":
            self.schedule_mode = "daily"
        self.auto_generate_video = self.schedule_mode != "manual"


class ConfigManager:
    """负责配置文件路径、加载和保存。"""

    def __init__(self, config_path: Path | None = None) -> None:
        self.project_dir = Path(__file__).resolve().parent.parent
        self.config_path = config_path or self.project_dir / "config" / "settings.json"
        self.log_dir = self.project_dir / "logs"
        self.logger = logging.getLogger("timelapse_studio.config")

    def load(self) -> AppConfig:
        """读取配置；文件损坏或字段过期时回退到默认值。"""
        if not self.config_path.exists():
            return AppConfig()

        try:
            with self.config_path.open("r", encoding="utf-8") as file:
                raw_data = json.load(file)
            if not isinstance(raw_data, dict):
                raise TypeError("配置文件根节点必须是 JSON 对象")
            data: dict[str, Any] = raw_data
            valid_names = {field.name for field in fields(AppConfig)}
            cleaned = {key: value for key, value in data.items() if key in valid_names}
            raw_devices = cleaned.pop("devices", None)
            config = AppConfig(**cleaned)
            if "schedule_mode" in data:
                config.auto_generate_video = config.schedule_mode != "manual"
            if "image_retention_policy" in data:
                config.delete_images_after_video = (
                    config.image_retention_policy == "delete_after_video"
                )
            if isinstance(raw_devices, list) and raw_devices:
                device_fields = {field.name for field in fields(DeviceConfig)}
                config.devices = [
                    DeviceConfig(
                        **{
                            key: value
                            for key, value in item.items()
                            if key in device_fields
                        }
                    )
                    for item in raw_devices
                    if isinstance(item, dict)
                ]
            else:
                config.devices = [
                    DeviceConfig(
                        name="海康威视摄像头 1",
                        rtsp_url=config.rtsp_url,
                        username=config.username,
                        password=config.password,
                    )
                ]
            config.sync_legacy_fields()
            return config
        except (OSError, json.JSONDecodeError, TypeError, ValueError) as error:
            self.logger.warning("配置文件读取失败，将使用默认配置: %s", error)
            return AppConfig()

    def save(self, config: AppConfig) -> bool:
        """保存配置并返回是否成功。"""
        try:
            config.sync_legacy_fields()
            self.config_path.parent.mkdir(parents=True, exist_ok=True)
            with self.config_path.open("w", encoding="utf-8") as file:
                json.dump(asdict(config), file, ensure_ascii=False, indent=2)
            return True
        except OSError as error:
            self.logger.error("配置文件保存失败: %s", error)
            return False
