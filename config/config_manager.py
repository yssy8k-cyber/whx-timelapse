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
    capture_interval: int = 60
    jpeg_quality: int = 95
    video_fps: int = 24
    delete_images_after_video: bool = False
    auto_generate_video: bool = False
    dark_mode: bool = False
    devices: list[DeviceConfig] = field(default_factory=lambda: [DeviceConfig()])
    active_device_index: int = 0

    def sync_legacy_fields(self) -> None:
        """同步旧版单设备字段，保证旧模块和配置文件兼容。"""
        if not self.devices:
            self.devices.append(DeviceConfig())
        self.active_device_index = max(0, min(self.active_device_index, len(self.devices) - 1))
        active_device = self.devices[self.active_device_index]
        self.rtsp_url = active_device.rtsp_url
        self.username = active_device.username
        self.password = active_device.password


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
                data: dict[str, Any] = json.load(file)
            valid_names = {field.name for field in fields(AppConfig)}
            cleaned = {key: value for key, value in data.items() if key in valid_names}
            raw_devices = cleaned.pop("devices", None)
            config = AppConfig(**cleaned)
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
