"""定时截图的图片目录和 JPEG 文件管理。"""

from __future__ import annotations

from datetime import datetime
from logging import Logger
from pathlib import Path

import cv2
import numpy as np

from utils.image_types import Frame


class ImageStorage:
    """将 OpenCV 图像保存到按日期划分的目录中。"""

    def __init__(self, root_directory: Path, jpeg_quality: int, logger: Logger) -> None:
        if not 1 <= jpeg_quality <= 100:
            raise ValueError("JPEG 质量必须在 1 到 100 之间")
        self.root_directory = Path(root_directory)
        self.jpeg_quality = jpeg_quality
        self.logger = logger

    def save_frame(self, frame: Frame, captured_at: datetime | None = None) -> Path:
        """保存一帧并返回文件路径；目录或写入失败时抛出异常。"""
        if not isinstance(frame, np.ndarray) or frame.size == 0:
            raise ValueError("待保存的图像为空")

        timestamp = captured_at or datetime.now()
        date_directory = self.root_directory / timestamp.strftime("%Y-%m-%d")
        date_directory.mkdir(parents=True, exist_ok=True)
        image_path = date_directory / f"{timestamp:%Y%m%d_%H%M%S}.jpg"
        parameters = [cv2.IMWRITE_JPEG_QUALITY, self.jpeg_quality]

        if not cv2.imwrite(str(image_path), frame, parameters):
            raise OSError(f"JPEG 写入失败: {image_path}")

        self.logger.info("截图成功: %s", image_path)
        return image_path
