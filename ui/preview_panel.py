"""实时预览卡片和 16:9 画面画布。"""

from __future__ import annotations

from time import monotonic

from PySide6.QtCore import QRect, QSize, Qt, QTimer
from PySide6.QtGui import QColor, QFont, QImage, QPainter, QPixmap
from PySide6.QtWidgets import (
    QFrame,
    QGraphicsDropShadowEffect,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)


class VideoPreviewWidget(QFrame):
    """保持视频比例绘制，并显示连接、REC 和画面统计信息。"""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("previewFrame")
        self.setMinimumSize(320, 180)
        policy = QSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        policy.setHeightForWidth(True)
        self.setSizePolicy(policy)
        self._image: QImage | None = None
        self._message = "未连接摄像头"
        self._stats_text = "FPS --  ·  分辨率 --"
        self._recording_started: float | None = None
        self._rec_label = QLabel(self)
        self._rec_label.setObjectName("recordingLabel")
        self._rec_label.setAlignment(Qt.AlignCenter)
        self._rec_label.hide()
        self._stats_label = QLabel(self._stats_text, self)
        self._stats_label.setObjectName("previewOverlayLabel")
        self._stats_label.adjustSize()
        self._rec_timer = QTimer(self)
        self._rec_timer.setInterval(1000)
        self._rec_timer.timeout.connect(self._update_recording_text)

    def hasHeightForWidth(self) -> bool:  # noqa: N802 - Qt API 名称
        return True

    def heightForWidth(self, width: int) -> int:  # noqa: N802 - Qt API 名称
        return max(180, round(width * 9 / 16))

    def sizeHint(self) -> QSize:  # noqa: N802 - Qt API 名称
        return QSize(640, 360)

    def set_message(self, message: str) -> None:
        """清除画面并显示连接状态文字。"""
        self._image = None
        self._message = message
        self._stats_text = "FPS --  ·  分辨率 --"
        self._stats_label.setText(self._stats_text)
        self._stats_label.adjustSize()
        self.update()

    def set_frame(self, image: QImage) -> None:
        """接收已经脱离 OpenCV 缓冲区的图像。"""
        self._image = image
        self._message = ""
        self.update()

    def set_stats(self, width: int, height: int, fps: float) -> None:
        """更新画面右下角的分辨率和 FPS。"""
        self._stats_text = f"FPS {fps:.1f}  ·  {width}×{height}"
        self._stats_label.setText(self._stats_text)
        self._stats_label.adjustSize()
        self._place_overlays()

    def set_recording(self, running: bool) -> None:
        """控制画面左上角的 REC 运行时间标识。"""
        if running:
            self._recording_started = monotonic()
            self._rec_label.show()
            self._rec_timer.start()
            self._update_recording_text()
        else:
            self._recording_started = None
            self._rec_timer.stop()
            self._rec_label.hide()

    def resizeEvent(self, event) -> None:  # noqa: N802 - Qt API 名称
        self._place_overlays()
        super().resizeEvent(event)

    def paintEvent(self, event) -> None:  # noqa: N802 - Qt API 名称
        del event
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor("#09111f"))
        if self._image is not None and not self._image.isNull():
            pixmap = QPixmap.fromImage(self._image).scaled(
                self.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation
            )
            x = (self.width() - pixmap.width()) // 2
            y = (self.height() - pixmap.height()) // 2
            painter.drawPixmap(x, y, pixmap)
        elif self._message:
            painter.setPen(QColor("#cbd5e1"))
            font = QFont(self.font())
            font.setPointSize(15)
            painter.setFont(font)
            painter.drawText(QRect(0, 0, self.width(), self.height()), Qt.AlignCenter, self._message)
        painter.end()

    def _place_overlays(self) -> None:
        self._rec_label.adjustSize()
        self._rec_label.move(14, 14)
        self._stats_label.adjustSize()
        self._stats_label.move(
            max(12, self.width() - self._stats_label.width() - 14),
            max(12, self.height() - self._stats_label.height() - 14),
        )

    def _update_recording_text(self) -> None:
        if self._recording_started is None:
            return
        elapsed = max(0, int(monotonic() - self._recording_started))
        hours, remainder = divmod(elapsed, 3600)
        minutes, seconds = divmod(remainder, 60)
        self._rec_label.setText(f"REC {hours:02d}:{minutes:02d}:{seconds:02d}")
        self._place_overlays()


class PreviewPanel(QFrame):
    """预览画面、实时状态和刷新操作的组合卡片。"""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("previewCard")
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(20)
        shadow.setOffset(0, 3)
        shadow.setColor(QColor(15, 23, 42, 30))
        self.setGraphicsEffect(shadow)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 18, 18, 16)
        layout.setSpacing(12)

        heading = QHBoxLayout()
        title = QLabel("实时画面预览")
        title.setObjectName("cardTitle")
        heading.addWidget(title)
        heading.addStretch()
        self.refresh_button = QPushButton("刷新预览")
        self.refresh_button.setObjectName("secondaryButton")
        self.refresh_button.setEnabled(False)
        heading.addWidget(self.refresh_button)
        layout.addLayout(heading)

        self.video_widget = VideoPreviewWidget(self)
        layout.addWidget(self.video_widget, 1)

        status_layout = QHBoxLayout()
        status_layout.setSpacing(12)
        self.connection_label = QLabel("连接状态：未连接")
        self.resolution_label = QLabel("分辨率：--")
        self.fps_label = QLabel("预览 FPS：--")
        self.stream_type_label = QLabel("码流：--")
        for label in (
            self.connection_label,
            self.resolution_label,
            self.fps_label,
            self.stream_type_label,
        ):
            label.setObjectName("previewStatusLabel")
            status_layout.addWidget(label)
        status_layout.addStretch()
        layout.addLayout(status_layout)

    def show_connecting(self) -> None:
        self.video_widget.set_message("正在连接摄像头...")
        self.connection_label.setText("连接状态：连接中")
        self.resolution_label.setText("分辨率：--")
        self.fps_label.setText("预览 FPS：--")
        self.stream_type_label.setText("码流：--")

    def show_connected(self, stream_type: str) -> None:
        self.connection_label.setText("连接状态：已连接")
        self.stream_type_label.setText(f"码流：{stream_type}")
        self.refresh_button.setEnabled(True)

    def show_not_connected(self) -> None:
        self.video_widget.set_recording(False)
        self.video_widget.set_message("未连接摄像头")
        self.connection_label.setText("连接状态：未连接")
        self.resolution_label.setText("分辨率：--")
        self.fps_label.setText("预览 FPS：--")
        self.stream_type_label.setText("码流：--")
        self.refresh_button.setEnabled(False)

    def show_connection_failed(self) -> None:
        self.video_widget.set_recording(False)
        self.video_widget.set_message("连接失败")
        self.connection_label.setText("连接状态：连接失败")
        self.resolution_label.setText("分辨率：--")
        self.fps_label.setText("预览 FPS：--")
        self.stream_type_label.setText("码流：--")
        self.refresh_button.setEnabled(True)

    def update_frame(self, image: QImage, width: int, height: int, fps: float) -> None:
        self.video_widget.set_frame(image)
        self.video_widget.set_stats(width, height, fps)
        self.resolution_label.setText(f"分辨率：{width}×{height}")
        self.fps_label.setText(f"预览 FPS：{fps:.1f}")

    def set_recording(self, running: bool) -> None:
        self.video_widget.set_recording(running)


__all__ = ["PreviewPanel", "VideoPreviewWidget"]
