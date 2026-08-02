"""线程安全的 RTSP 视频流封装。"""

from __future__ import annotations

import logging
from logging import Logger
from threading import RLock
from typing import Callable, Protocol
from urllib.parse import quote

try:
    import cv2
except ImportError:  # 依赖缺失时由上层显示可读错误，不让 GUI 直接崩溃
    cv2 = None

from utils.image_types import Frame


class VideoCaptureLike(Protocol):
    """OpenCV VideoCapture 所需的最小接口，便于单元测试替换。"""

    def set(self, property_id: int, value: float) -> bool: ...

    def isOpened(self) -> bool: ...

    def read(self) -> tuple[bool, Frame | None]: ...

    def release(self) -> None: ...


CaptureFactory = Callable[[str], VideoCaptureLike]


class RTSPStreamError(RuntimeError):
    """RTSP 视频流连接或读取异常。"""


class RTSPStream:
    """封装 VideoCapture，并允许其他线程安全读取视频帧。"""

    def __init__(
        self,
        logger: Logger | None = None,
        capture_factory: CaptureFactory | None = None,
    ) -> None:
        self.logger = logger or logging.getLogger(__name__)
        self._capture_factory = capture_factory or self._create_capture
        self._capture: VideoCaptureLike | None = None
        self._lock = RLock()

    @property
    def is_connected(self) -> bool:
        """返回当前视频流是否处于打开状态。"""
        with self._lock:
            return self._capture is not None and self._capture.isOpened()

    def connect(self, rtsp_url: str, username: str, password: str) -> None:
        """打开 RTSP 并读取首帧，失败时抛出 RTSPStreamError。"""
        full_url = build_rtsp_url(rtsp_url, username, password)
        if not full_url:
            raise RTSPStreamError("RTSP 地址不能为空")
        if cv2 is None:
            raise RTSPStreamError("未安装 OpenCV，请先安装项目依赖")

        with self._lock:
            self._release_capture_locked()
            try:
                capture = self._capture_factory(full_url)
                if hasattr(cv2, "CAP_PROP_OPEN_TIMEOUT_MSEC"):
                    capture.set(cv2.CAP_PROP_OPEN_TIMEOUT_MSEC, 5000)
                if not capture.isOpened():
                    capture.release()
                    raise RTSPStreamError("无法打开 RTSP 视频流")

                success, frame = capture.read()
                if not success or frame is None:
                    capture.release()
                    raise RTSPStreamError("RTSP 已打开，但读取首帧失败")

                self._capture = capture
            except RTSPStreamError:
                raise
            except Exception as error:
                self.logger.exception("打开 RTSP 视频流时发生异常")
                raise RTSPStreamError(f"连接异常: {error}") from error

    def read_frame(self) -> Frame | None:
        """读取一帧副本，读取失败返回 None。"""
        with self._lock:
            if self._capture is None:
                return None
            try:
                success, frame = self._capture.read()
                if not success or frame is None:
                    return None
                return frame.copy()
            except Exception:
                self.logger.exception("读取 RTSP 视频帧时发生异常")
                return None

    def disconnect(self) -> None:
        """安全释放 VideoCapture。"""
        with self._lock:
            capture = self._capture
            self._capture = None
            if capture is None:
                return
            try:
                capture.release()
            except Exception:
                self.logger.exception("释放 RTSP 视频流时发生异常")

    def _release_capture_locked(self) -> None:
        capture = self._capture
        self._capture = None
        if capture is None:
            return
        try:
            capture.release()
        except Exception:
            self.logger.exception("释放旧 RTSP 视频流时发生异常")

    @staticmethod
    def _create_capture(rtsp_url: str) -> VideoCaptureLike:
        if cv2 is None:
            raise RTSPStreamError("未安装 OpenCV")
        return cv2.VideoCapture(rtsp_url, cv2.CAP_FFMPEG)


def build_rtsp_url(rtsp_url: str, username: str, password: str) -> str:
    """给 RTSP 地址补充 URL 编码后的鉴权信息。"""
    url = rtsp_url.strip()
    if not url or (not username and not password):
        return url
    if "://" not in url:
        return url
    scheme, remainder = url.split("://", 1)
    if "@" in remainder:
        return url
    credentials = f"{quote(username, safe='')}:{quote(password, safe='')}"
    return f"{scheme}://{credentials}@{remainder}"
