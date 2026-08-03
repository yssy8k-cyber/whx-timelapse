"""实时 RTSP 预览控制器。

预览使用独立的 VideoCapture 和 Python 工作线程，不读取截图线程使用的
视频流，从而避免预览刷新影响定时截图的时间精度。
"""

from __future__ import annotations

import logging
from logging import Logger
from threading import Event, Lock, Thread, current_thread
from time import monotonic
from typing import Callable, Protocol

try:
    import cv2
except ImportError:  # 依赖缺失时通过状态信号反馈给界面
    cv2 = None

from PySide6.QtCore import QObject, Signal
from PySide6.QtGui import QImage

from utils.image_types import Frame

from .rtsp_stream import RTSPStream, RTSPStreamError


class PreviewStream(Protocol):
    """预览线程所需的视频流接口，便于测试时替换。"""

    def connect(self, rtsp_url: str, username: str, password: str) -> None: ...

    def read_frame(self) -> Frame | None: ...

    def disconnect(self) -> None: ...


StreamFactory = Callable[[Logger], PreviewStream]
PreviewFrame = tuple[QImage, int, int, float]


class PreviewWorker:
    """以受限帧率读取 RTSP，并将帧转换为 Qt 图像。"""

    def __init__(
        self,
        rtsp_url: str,
        username: str,
        password: str,
        logger: Logger,
        on_frame: Callable[[QImage, int, int, float], None],
        on_connected: Callable[[], None],
        on_error: Callable[[str], None],
        on_finished: Callable[[], None],
        target_fps: float = 12.0,
        stream_factory: StreamFactory | None = None,
    ) -> None:
        if not 10.0 <= target_fps <= 15.0:
            raise ValueError("预览 FPS 必须在 10 到 15 之间")
        self.rtsp_url = rtsp_url
        self.username = username
        self.password = password
        self.logger = logger
        self.on_frame = on_frame
        self.on_connected = on_connected
        self.on_error = on_error
        self.on_finished = on_finished
        self.target_fps = target_fps
        self._stream_factory = stream_factory or (
            lambda worker_logger: RTSPStream(worker_logger)
        )
        self._stop_event = Event()

    def stop(self) -> None:
        """请求预览循环退出。"""
        self._stop_event.set()

    def run(self) -> None:
        """执行预览循环，并确保底层流在所有路径上释放。"""
        stream: PreviewStream | None = None
        try:
            stream = self._stream_factory(self.logger)
            stream.connect(self.rtsp_url, self.username, self.password)
            self.logger.info("实时预览连接成功: %s", self.rtsp_url)
            self.on_connected()
            self._run_stream(stream)
        except RTSPStreamError as error:
            self.logger.error("实时预览连接失败: %s", error)
            self.on_error(str(error))
        except Exception as error:  # 预览异常不能导致 GUI 退出
            self.logger.exception("实时预览线程发生异常")
            self.on_error(f"预览异常: {error}")
        finally:
            if stream is not None:
                try:
                    stream.disconnect()
                except Exception:
                    self.logger.exception("释放实时预览视频流失败")
            try:
                self.on_finished()
            except Exception:
                self.logger.exception("实时预览结束回调执行失败")

    def _run_stream(self, stream: PreviewStream) -> None:
        frame_interval = 1.0 / self.target_fps
        measured_frames = 0
        measured_started = monotonic()
        while not self._stop_event.is_set():
            started = monotonic()
            frame = stream.read_frame()
            if frame is None:
                self.on_error("预览读取视频帧失败")
                return
            image = _frame_to_qimage(frame)
            measured_frames += 1
            elapsed = monotonic() - measured_started
            measured_fps = measured_frames / elapsed if elapsed > 0 else 0.0
            measured_fps = min(self.target_fps, measured_fps)
            self.on_frame(image, frame.shape[1], frame.shape[0], measured_fps)
            wait_seconds = max(0.0, frame_interval - (monotonic() - started))
            if self._stop_event.wait(wait_seconds):
                return
            if elapsed >= 1.0:
                measured_frames = 0
                measured_started = monotonic()


class PreviewController(QObject):
    """管理实时预览线程，并通过 Qt 信号更新 GUI。"""

    # 只通知 GUI “有新帧”，图像本身在锁保护的单槽缓冲区中传递。
    frame_ready = Signal()
    connected = Signal()
    error = Signal(str)
    finished = Signal()
    running_changed = Signal(bool)

    def __init__(
        self,
        logger: Logger | None = None,
        parent: QObject | None = None,
        stream_factory: StreamFactory | None = None,
    ) -> None:
        super().__init__(parent)
        self.logger = logger or logging.getLogger("timelapse_studio.preview")
        self.stream_factory = stream_factory
        self._state_lock = Lock()
        self._frame_lock = Lock()
        self._latest_frame: PreviewFrame | None = None
        self._frame_pending = False
        self._worker: PreviewWorker | None = None
        self._thread: Thread | None = None

    @property
    def is_running(self) -> bool:
        """返回预览线程是否正在运行。"""
        with self._state_lock:
            return self._thread is not None and self._thread.is_alive()

    def start(self, rtsp_url: str, username: str, password: str) -> bool:
        """启动预览；已有预览会先被停止。"""
        if not rtsp_url.strip():
            self.error.emit("RTSP 地址不能为空")
            return False
        self.stop()
        worker = PreviewWorker(
            rtsp_url=rtsp_url,
            username=username,
            password=password,
            logger=self.logger,
            on_frame=self._publish_frame,
            on_connected=self.connected.emit,
            on_error=self.error.emit,
            on_finished=self._on_worker_finished,
            stream_factory=self.stream_factory,
        )
        thread = Thread(target=worker.run, name="timelapse-preview", daemon=True)
        with self._state_lock:
            self._worker = worker
            self._thread = thread
        thread.start()
        self.running_changed.emit(True)
        self.logger.info("实时预览线程已启动")
        return True

    def take_latest_frame(self) -> PreviewFrame | None:
        """取出最新预览帧，并允许工作线程发送下一次通知。"""
        with self._frame_lock:
            frame = self._latest_frame
            self._latest_frame = None
            self._frame_pending = False
            return frame

    def stop(self, timeout: float = 6.0) -> bool:
        """停止预览并等待资源释放。"""
        with self._state_lock:
            worker = self._worker
            thread = self._thread
        if worker is None or thread is None:
            return True
        worker.stop()
        if thread is not current_thread():
            thread.join(timeout)
        stopped = not thread.is_alive()
        if stopped:
            with self._state_lock:
                if self._thread is thread:
                    self._thread = None
                    self._worker = None
            with self._frame_lock:
                self._latest_frame = None
                self._frame_pending = False
            self.running_changed.emit(False)
            self.logger.info("实时预览线程已停止")
        else:
            self.logger.warning("实时预览线程停止超时")
        return stopped

    def shutdown(self) -> None:
        """关闭预览控制器。"""
        self.stop()

    def _on_worker_finished(self) -> None:
        """处理自然退出，避免控制器保留已结束线程对象。"""
        with self._state_lock:
            thread = self._thread
            if thread is not current_thread():
                return
            self._thread = None
            self._worker = None
        self.running_changed.emit(False)
        self.finished.emit()

    def _publish_frame(
        self,
        image: QImage,
        width: int,
        height: int,
        fps: float,
    ) -> None:
        """写入单槽最新帧缓冲，避免 Qt 事件队列无限积压图像。"""
        with self._frame_lock:
            self._latest_frame = (image, width, height, fps)
            if self._frame_pending:
                return
            self._frame_pending = True
        self.frame_ready.emit()


def _frame_to_qimage(frame: Frame) -> QImage:
    """将 OpenCV 的 BGR 帧复制为线程安全的 RGB QImage。"""
    if cv2 is None:
        raise RuntimeError("未安装 OpenCV，无法显示实时预览")
    if frame.ndim != 3 or frame.shape[2] != 3:
        raise ValueError("预览帧格式不是 3 通道彩色图像")
    rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    height, width, channels = rgb_frame.shape
    return QImage(
        rgb_frame.data,
        width,
        height,
        width * channels,
        QImage.Format.Format_RGB888,
    ).copy()


def stream_type_from_url(rtsp_url: str) -> str:
    """根据海康威视通道号推断码流类型，无法判断时返回未知。"""
    path = rtsp_url.lower().split("?", 1)[0]
    if "/102" in path or "substream" in path:
        return "子码流"
    if "/101" in path or "mainstream" in path:
        return "主码流"
    return "未知码流"


__all__ = [
    "PreviewController",
    "PreviewWorker",
    "stream_type_from_url",
]
