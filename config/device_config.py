"""摄像头设备配置模型。"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class DeviceConfig:
    """一个 RTSP 摄像头的连接配置。"""

    name: str = "海康威视摄像头 1"
    rtsp_url: str = ""
    username: str = ""
    password: str = ""
