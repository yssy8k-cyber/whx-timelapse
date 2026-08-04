"""VideoMaker_Test：独立验证图片序列转 H.264 MP4 的桌面工具。"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

from PySide6.QtCore import QObject, QThread, Signal, Slot
from PySide6.QtWidgets import (
    QApplication,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from video.video_generator import VideoConfig, VideoGenerator


class VideoMakerWorker(QObject):
    """在独立线程中执行图片扫描、序列准备和 FFmpeg 调用。"""

    progress = Signal(int, int, str)
    succeeded = Signal(str)
    failed = Signal(str)

    def __init__(self, image_directory: Path, output_path: Path, fps: int) -> None:
        super().__init__()
        self.image_directory = image_directory
        self.output_path = output_path
        self.fps = fps

    @Slot()
    def run(self) -> None:
        try:
            generator = VideoGenerator(VideoConfig(fps=self.fps), logging.getLogger("video-maker-test"))
            output = generator.generate(
                self.image_directory,
                self.output_path,
                lambda completed, total, message: self.progress.emit(completed, total, message),
            )
            self.succeeded.emit(str(output))
        except Exception as error:
            self.failed.emit(str(error))


class VideoMakerTestWindow(QMainWindow):
    """独立视频能力验证窗口。"""

    def __init__(self) -> None:
        super().__init__()
        self.thread: QThread | None = None
        self.worker: VideoMakerWorker | None = None
        self.setWindowTitle("VideoMaker_Test - Hikvision Time-Lapse Client")
        self.resize(760, 360)
        self._build_ui()
        self.setStyleSheet(
            """
            QWidget { font-family: 'Segoe UI', 'Microsoft YaHei'; font-size: 13px; }
            QMainWindow, QWidget { background: #171a1f; color: #f3f4f6; }
            QLineEdit, QSpinBox { background: #24282f; border: 1px solid #49515c; padding: 7px; border-radius: 5px; }
            QPushButton { background: #1677d2; border: 0; padding: 8px 16px; border-radius: 5px; color: white; }
            QPushButton:disabled { background: #4b5563; }
            QProgressBar { border: 1px solid #49515c; border-radius: 5px; text-align: center; }
            QProgressBar::chunk { background: #22c55e; }
            """
        )

    def _build_ui(self) -> None:
        root = QWidget(self)
        layout = QVBoxLayout(root)
        form = QFormLayout()

        self.image_edit = QLineEdit()
        self.image_edit.setPlaceholderText("TestImages 或日期图片目录")
        image_row = QHBoxLayout()
        image_row.addWidget(self.image_edit)
        image_browse = QPushButton("浏览")
        image_browse.clicked.connect(self._choose_image_directory)
        image_row.addWidget(image_browse)
        form.addRow("图片目录", image_row)

        self.output_edit = QLineEdit()
        self.output_edit.setPlaceholderText("输出 MP4 路径")
        output_row = QHBoxLayout()
        output_row.addWidget(self.output_edit)
        output_browse = QPushButton("浏览")
        output_browse.clicked.connect(self._choose_output_path)
        output_row.addWidget(output_browse)
        form.addRow("输出文件", output_row)

        self.fps_spin = QSpinBox()
        self.fps_spin.setRange(1, 120)
        self.fps_spin.setValue(25)
        form.addRow("视频帧率", self.fps_spin)
        layout.addLayout(form)

        self.status_label = QLabel("支持验证：1000 / 5000 / 10000 / 30000 张图片")
        layout.addWidget(self.status_label)
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        layout.addWidget(self.progress_bar)
        self.start_button = QPushButton("开始验证")
        self.start_button.clicked.connect(self._start)
        layout.addWidget(self.start_button)
        self.setCentralWidget(root)

    def _choose_image_directory(self) -> None:
        directory = QFileDialog.getExistingDirectory(self, "选择测试图片目录")
        if directory:
            self.image_edit.setText(directory)
            if not self.output_edit.text().strip():
                self.output_edit.setText(str(Path(directory).parent / f"{Path(directory).name}.mp4"))

    def _choose_output_path(self) -> None:
        filename, _ = QFileDialog.getSaveFileName(self, "选择 MP4 输出文件", "timelapse.mp4", "MP4 视频 (*.mp4)")
        if filename:
            self.output_edit.setText(filename)

    def _start(self) -> None:
        image_directory = Path(self.image_edit.text().strip())
        output_path = Path(self.output_edit.text().strip())
        if not image_directory.is_dir():
            QMessageBox.warning(self, "无法开始", "请选择存在的图片目录。")
            return
        if not output_path.name:
            QMessageBox.warning(self, "无法开始", "请指定 MP4 输出文件。")
            return

        self.start_button.setEnabled(False)
        self.progress_bar.setValue(0)
        self.status_label.setText("正在扫描和准备图片...")
        self.thread = QThread(self)
        self.worker = VideoMakerWorker(image_directory, output_path, self.fps_spin.value())
        self.worker.moveToThread(self.thread)
        self.thread.started.connect(self.worker.run)
        self.worker.progress.connect(self._on_progress)
        self.worker.succeeded.connect(self._on_success)
        self.worker.failed.connect(self._on_failure)
        self.worker.succeeded.connect(self.thread.quit)
        self.worker.failed.connect(self.thread.quit)
        self.thread.finished.connect(self._task_finished)
        self.thread.start()

    def _on_progress(self, completed: int, total: int, message: str) -> None:
        if message == "视频生成完成":
            percent = 100
        elif message == "正在调用 FFmpeg":
            percent = 90
        else:
            percent = round(completed * 80 / total) if total else 0
        self.progress_bar.setValue(percent)
        self.status_label.setText(f"{message}  {completed:,}/{total:,}  ({percent}%)")

    def _on_success(self, output_path: str) -> None:
        self.progress_bar.setValue(100)
        self.status_label.setText(f"验证成功：{output_path}")
        QMessageBox.information(self, "VideoMaker_Test", f"视频已生成：\n{output_path}")

    def _on_failure(self, message: str) -> None:
        self.status_label.setText("验证失败")
        QMessageBox.critical(self, "VideoMaker_Test", message)

    def _task_finished(self) -> None:
        self.start_button.setEnabled(True)
        if self.worker is not None:
            self.worker.deleteLater()
        if self.thread is not None:
            self.thread.deleteLater()
        self.worker = None
        self.thread = None

    def closeEvent(self, event) -> None:  # noqa: N802 - Qt API 名称
        if self.thread is not None and self.thread.isRunning():
            self.thread.quit()
            self.thread.wait(3000)
        super().closeEvent(event)


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("VideoMaker_Test")
    window = VideoMakerTestWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
