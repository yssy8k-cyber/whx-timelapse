"""RTSP 断流检测和自动重连。"""

from __future__ import annotations

import logging
from logging import Logger
from threading import Event, Lock, Thread, current_thread
from typing import Protocol

from utils.image_types import Frame


class StreamClient(Protocol):
    """重连管理器依赖的最小视频流接口。"""

    def connect(self, rtsp_url: str, username: str, password: str) -> None: ...

    def read_frame(self) -> Frame | None: ...

    def disconnect(self) -> None: ...


class RTSPReconnectManager:
    """连接成功后检测空帧，并按固定间隔自动重连。"""

    def __init__(
        self,
        stream: StreamClient,
        logger: Logger | None = None,
        reconnect_interval_seconds: float = 10.0,
    ) -> None:
        if reconnect_interval_seconds <= 0:
            raise ValueError("重连间隔必须大于 0 秒")
        self.stream = stream
        self.logger = logger or logging.getLogger(__name__)
        self.reconnect_interval_seconds = reconnect_interval_seconds
        self._state_lock = Lock()
        self._stop_event = Event()
        self._reconnect_requested = Event()
        self._thread: Thread | None = None
        self._credentials: tuple[str, str, str] | None = None
        self._active = False

    def connect(self, rtsp_url: str, username: str, password: str) -> None:
        """执行首次连接；首次失败交由上层显示，不自动循环重试。"""
        with self._state_lock:
            self._credentials = (rtsp_url, username, password)
            self._active = True
            self._stop_event.clear()
            self._reconnect_requested.clear()
        try:
            self.stream.connect(rtsp_url, username, password)
        except Exception:
            with self._state_lock:
                self._active = False
            raise
        self._ensure_reconnect_thread()

    def read_frame(self) -> Frame | None:
        """读取视频帧；空帧会触发后台自动重连。"""
        frame = self.stream.read_frame()
        if frame is None:
            self._request_reconnect()
        return frame

    def disconnect(self) -> None:
        """停止重连等待并释放底层视频流。"""
        with self._state_lock:
            self._active = False
            self._credentials = None
            self._stop_event.set()
            # 唤醒可能正在等待断流事件的线程，让它立即检查停止状态。
            self._reconnect_requested.set()
            thread = self._thread
        if thread is not None and thread is not current_thread():
            thread.join(3.0)
        self.stream.disconnect()
        with self._state_lock:
            if self._thread is thread and (thread is None or not thread.is_alive()):
                self._thread = None

    def _ensure_reconnect_thread(self) -> None:
        with self._state_lock:
            if self._thread is not None and self._thread.is_alive():
                return
            self._thread = Thread(
                target=self._reconnect_loop,
                name="timelapse-rtsp-reconnect",
                daemon=True,
            )
            self._thread.start()

    def _request_reconnect(self) -> None:
        with self._state_lock:
            if not self._active or self._credentials is None:
                return
            already_requested = self._reconnect_requested.is_set()
            self._reconnect_requested.set()
        if not already_requested:
            self.logger.warning(
                "检测到 RTSP 断流，将在 %.1f 秒后自动重连",
                self.reconnect_interval_seconds,
            )

    def _reconnect_loop(self) -> None:
        while not self._stop_event.is_set():
            if not self._reconnect_requested.wait():
                return
            self._reconnect_requested.clear()
            if self._stop_event.is_set():
                return
            if self._stop_event.wait(self.reconnect_interval_seconds):
                return
            self._attempt_reconnect()

    def _attempt_reconnect(self) -> None:
        with self._state_lock:
            credentials = self._credentials
            active = self._active
        if not active or credentials is None:
            return

        self.logger.info("开始自动重连 RTSP")
        try:
            self.stream.connect(*credentials)
        except Exception as error:
            self.logger.error("自动重连失败: %s", error)
            self._request_reconnect()
            return

        with self._state_lock:
            still_active = self._active
        if still_active:
            self.logger.info("自动重连成功")
        else:
            self.stream.disconnect()
