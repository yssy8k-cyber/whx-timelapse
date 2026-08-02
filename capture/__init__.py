"""定时截图模块。"""

from .capture_worker import CaptureConfig, CaptureWorker
from .image_storage import ImageStorage

__all__ = ["CaptureConfig", "CaptureWorker", "ImageStorage"]
