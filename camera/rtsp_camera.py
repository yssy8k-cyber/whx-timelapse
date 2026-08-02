"""RTSP 摄像头的 Qt 工作线程控制器。"""

from __future__ import annotations

import logging

from PySide6.QtCore import QObject, QThread, Signal, Slot

from utils.image_types import Frame

from .rtsp_reconnect import RTSPReconnectManager
from .rtsp_stream import RTSPStream, RTSPStreamError, build_rtsp_url


class CameraWorker(QObject):
    """运行在 Qt 后台线程中的连接工作对象。"""

    connection_succeeded = Signal(str)
    connection_failed = Signal(str)
    disconnected = Signal()

    def __init__(self, stream: RTSPReconnectManager, logger: logging.Logger) -> None:
        super().__init__()
        self._stream = stream
        self.logger = logger

    @Slot(str, str, str)
    def connect_camera(self, rtsp_url: str, username: str, password: str) -> None:
        """打开 RTSP 并读取首帧，确认地址和鉴权可用。"""
        try:
            self._stream.connect(rtsp_url, username, password)
            self.logger.info("连接成功: %s", rtsp_url)
            self.connection_succeeded.emit(rtsp_url)
        except RTSPStreamError as error:
            self.logger.error("连接失败: %s", error)
            self.connection_failed.emit(str(error))
        except Exception as error:  # 摄像头驱动异常不能让 GUI 崩溃
            self.logger.exception("连接 RTSP 时发生未预期异常")
            self.connection_failed.emit(f"连接异常: {error}")

    @Slot()
    def disconnect_camera(self) -> None:
        """释放当前视频流。"""
        self._stream.disconnect()
        self.disconnected.emit()


class CameraController(QObject):
    """在主线程、摄像头线程和截图线程之间提供安全边界。"""

    request_connect = Signal(str, str, str)
    request_disconnect = Signal()
    connection_succeeded = Signal(str)
    connection_failed = Signal(str)
    disconnected = Signal()

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self.logger = logging.getLogger("timelapse_studio.camera")
        self._stream = RTSPReconnectManager(RTSPStream(self.logger), self.logger)
        self._thread = QThread(self)
        self._worker = CameraWorker(self._stream, self.logger)
        self._worker.moveToThread(self._thread)
        self.request_connect.connect(self._worker.connect_camera)
        self.request_disconnect.connect(self._worker.disconnect_camera)
        self._worker.connection_succeeded.connect(self.connection_succeeded)
        self._worker.connection_failed.connect(self.connection_failed)
        self._worker.disconnected.connect(self.disconnected)
        self._thread.finished.connect(self._worker.deleteLater)
        self._thread.start()

    def connect_camera(self, rtsp_url: str, username: str, password: str) -> None:
        """请求摄像头线程测试 RTSP 连接。"""
        self.request_connect.emit(rtsp_url, username, password)

    def read_frame(self) -> Frame | None:
        """为截图线程提供一帧副本，不直接暴露 VideoCapture。"""
        return self._stream.read_frame()

    def disconnect_camera(self) -> None:
        """请求摄像头线程断开 RTSP 连接。"""
        self.request_disconnect.emit()

    def shutdown(self) -> None:
        """在应用退出时释放视频流和 Qt 工作线程。"""
        self.request_disconnect.emit()
        self._thread.quit()
        self._thread.wait(3000)


__all__ = ["CameraController", "CameraWorker", "build_rtsp_url"]
