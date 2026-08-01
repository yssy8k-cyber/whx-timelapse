"""Native PyQt6 control window for the timelapse pipeline."""

from __future__ import annotations

import os
import sys
import threading
from pathlib import Path

from PyQt6.QtCore import QObject, QThread, QTimer, Qt, pyqtSignal, pyqtSlot
from PyQt6.QtGui import QColor, QFont, QIcon, QPainter, QPixmap
from PyQt6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QFileDialog,
    QFormLayout,
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMenu,
    QMessageBox,
    QPushButton,
    QProgressBar,
    QScrollArea,
    QSizePolicy,
    QSpinBox,
    QSplitter,
    QStatusBar,
    QVBoxLayout,
    QWidget,
)

from .capture import CaptureConfig
from .pipeline import capture_and_render
from .render import find_images, render


def resource_path(relative: str) -> Path:
    """Resolve a bundled resource in source and PyInstaller environments."""

    relative_path = Path(relative)
    candidates: list[Path] = []
    meipass = getattr(sys, "_MEIPASS", None)
    if meipass:
        bundle_root = Path(meipass)
        candidates.extend(
            [
                bundle_root / relative_path,
                bundle_root.parent / "Resources" / relative_path,
                bundle_root.parent / "Frameworks" / relative_path,
            ]
        )

    package_dir = Path(__file__).resolve().parent
    source_src = package_dir.parent
    project_root = source_src.parent
    candidates.extend(
        [
            source_src / relative_path,
            package_dir / relative_path,
            project_root / relative_path,
        ]
    )
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    raise FileNotFoundError(f"找不到资源文件: {relative}")


def _bundle_roots() -> list[Path]:
    meipass = getattr(sys, "_MEIPASS", None)
    if meipass:
        root = Path(meipass)
        return [root, root.parent / "Resources", root.parent / "Frameworks"]
    project_root = Path(__file__).resolve().parents[2]
    return [project_root, project_root / "assets"]


def _asset_path(name: str) -> Path | None:
    for root in _bundle_roots():
        candidates = [root / "timelapse" / "assets" / name, root / "assets" / name]
        for candidate in candidates:
            if candidate.is_file():
                return candidate
    return None


def _find_ffmpeg() -> str:
    configured = os.getenv("FFMPEG_BIN")
    if configured and Path(configured).is_file():
        return configured
    binary_name = "ffmpeg.exe" if sys.platform == "win32" else "ffmpeg"
    for root in _bundle_roots():
        bin_dir = root / "bin"
        direct = bin_dir / binary_name
        if direct.is_file():
            return str(direct)
        if bin_dir.is_dir():
            for candidate in sorted(bin_dir.rglob("*")):
                if candidate.is_file() and candidate.name.lower().startswith("ffmpeg"):
                    return str(candidate)
    return binary_name


class JobWorker(QObject):
    """Run one capture/render job outside the Qt event loop."""

    finished = pyqtSignal(object)
    failed = pyqtSignal(str)

    def __init__(self, kind: str, *, config: CaptureConfig | None = None, output: Path | None = None, fps: float = 24, crf: int = 18, preset: str = "medium", overwrite: bool = False) -> None:
        super().__init__()
        self.kind = kind
        self.config = config
        self.output = output
        self.fps = fps
        self.crf = crf
        self.preset = preset
        self.overwrite = overwrite
        self.stop_event = threading.Event()

    @pyqtSlot()
    def run(self) -> None:
        try:
            if self.kind == "pipeline" and self.config is not None and self.output is not None:
                result = capture_and_render(
                    self.config,
                    self.stop_event,
                    self.output,
                    fps=self.fps,
                    crf=self.crf,
                    preset=self.preset,
                    overwrite=self.overwrite,
                )
            elif self.kind == "render" and self.config is not None and self.output is not None:
                result = render(
                    self.config.output_dir,
                    self.output,
                    fps=self.fps,
                    ffmpeg_bin=self.config.ffmpeg_bin,
                    crf=self.crf,
                    preset=self.preset,
                    overwrite=self.overwrite,
                )
            else:
                raise RuntimeError("任务参数不完整。")
        except Exception as exc:
            self.failed.emit(str(exc))
        else:
            self.finished.emit(result)

    def stop(self) -> None:
        self.stop_event.set()


class Panel(QGroupBox):
    def __init__(self, title: str, subtitle: str) -> None:
        super().__init__()
        self.setTitle("")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 18, 20, 20)
        layout.setSpacing(14)
        heading = QHBoxLayout()
        heading.setSpacing(10)
        text = QVBoxLayout()
        text.setSpacing(2)
        kicker = QLabel(subtitle)
        kicker.setObjectName("panelKicker")
        heading_label = QLabel(title)
        heading_label.setObjectName("panelTitle")
        text.addWidget(kicker)
        text.addWidget(heading_label)
        heading.addLayout(text)
        heading.addStretch()
        layout.addLayout(heading)


class TimelapseWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self._thread: QThread | None = None
        self._worker: JobWorker | None = None
        self._busy = False
        self._latest_frames: list[Path] = []
        self._build_window()
        self._build_menu()
        self._apply_style()
        self._poll_timer = QTimer(self)
        self._poll_timer.timeout.connect(self._refresh_preview)
        self._poll_timer.start(1000)

    def _build_window(self) -> None:
        self.setWindowTitle("WHX 延时摄影自动化工具")
        self.setMinimumSize(1080, 720)
        self.resize(1280, 820)
        icon = _asset_path("app.icns") or _asset_path("app.ico")
        if icon:
            self.setWindowIcon(QIcon(str(icon)))

        central = QWidget()
        central.setObjectName("central")
        self.setCentralWidget(central)
        outer = QVBoxLayout(central)
        outer.setContentsMargins(26, 22, 26, 22)
        outer.setSpacing(18)

        header = QHBoxLayout()
        brand = QVBoxLayout()
        brand.setSpacing(2)
        eyebrow = QLabel("LOCAL DESKTOP WORKSPACE")
        eyebrow.setObjectName("eyebrow")
        title = QLabel("WHX 延时摄影自动化工具")
        title.setObjectName("windowTitle")
        brand.addWidget(eyebrow)
        brand.addWidget(title)
        header.addLayout(brand)
        header.addStretch()
        self.status_badge = QLabel("●  就绪")
        self.status_badge.setObjectName("statusBadge")
        header.addWidget(self.status_badge, alignment=Qt.AlignmentFlag.AlignTop)
        outer.addLayout(header)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        body = QWidget()
        body_layout = QVBoxLayout(body)
        body_layout.setContentsMargins(0, 0, 0, 0)
        body_layout.setSpacing(16)
        main_split = QSplitter(Qt.Orientation.Horizontal)
        main_split.setChildrenCollapsible(False)
        main_split.setHandleWidth(10)
        main_split.addWidget(self._build_capture_panel())
        main_split.addWidget(self._build_preview_panel())
        main_split.setStretchFactor(0, 1)
        main_split.setStretchFactor(1, 1)
        body_layout.addWidget(main_split, 1)
        lower_split = QSplitter(Qt.Orientation.Horizontal)
        lower_split.setChildrenCollapsible(False)
        lower_split.setHandleWidth(10)
        lower_split.addWidget(self._build_render_panel())
        lower_split.addWidget(self._build_activity_panel())
        lower_split.setStretchFactor(0, 1)
        lower_split.setStretchFactor(1, 1)
        body_layout.addWidget(lower_split)
        scroll.setWidget(body)
        outer.addWidget(scroll, 1)

        self.setStatusBar(QStatusBar())
        self.statusBar().showMessage("准备就绪")

    def _build_capture_panel(self) -> QWidget:
        panel = Panel("采集配置", "01 / SOURCE")
        layout = panel.layout()
        assert layout is not None
        form = QFormLayout()
        form.setHorizontalSpacing(14)
        form.setVerticalSpacing(12)
        self.rtsp_edit = QLineEdit()
        self.rtsp_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.rtsp_edit.setPlaceholderText("rtsp://用户名:密码@摄像头IP:554/Streaming/Channels/101")
        form.addRow("视频流地址", self.rtsp_edit)
        self.interval_spin = QDoubleSpinBox()
        self.interval_spin.setRange(0.1, 86400)
        self.interval_spin.setSingleStep(0.5)
        self.interval_spin.setValue(10)
        form.addRow("抽帧间隔（秒）", self.interval_spin)
        self.stop_mode = QComboBox()
        self.stop_mode.addItem("图片数量", "count")
        self.stop_mode.addItem("运行时长（分钟）", "duration")
        self.stop_mode.currentIndexChanged.connect(self._update_stop_label)
        form.addRow("停止条件", self.stop_mode)
        self.stop_value = QSpinBox()
        self.stop_value.setRange(1, 1_000_000)
        self.stop_value.setValue(360)
        self.stop_value_label = QLabel("目标图片数")
        form.addRow(self.stop_value_label, self.stop_value)
        self.transport = QComboBox()
        self.transport.addItems(["tcp", "udp", "http", "https"])
        form.addRow("传输方式", self.transport)
        self.capture_dir = self._path_row(form, "图片目录", "captures", directory=True)
        self.ffmpeg_edit = QLineEdit(_find_ffmpeg())
        form.addRow("FFmpeg 路径", self.ffmpeg_edit)
        layout.addLayout(form)

        actions = QHBoxLayout()
        self.start_button = QPushButton("▶  开始采集")
        self.start_button.setObjectName("primaryButton")
        self.start_button.clicked.connect(self._start_capture)
        self.stop_button = QPushButton("■  停止任务")
        self.stop_button.setObjectName("dangerButton")
        self.stop_button.clicked.connect(self._stop_job)
        self.stop_button.setEnabled(False)
        actions.addWidget(self.start_button)
        actions.addWidget(self.stop_button)
        layout.addLayout(actions)
        note = QLabel("采集自然结束后，将自动合成 MP4。RTSP 地址只在本机处理。")
        note.setObjectName("mutedLabel")
        note.setWordWrap(True)
        layout.addWidget(note)
        return panel

    def _build_preview_panel(self) -> QWidget:
        panel = Panel("最新画面", "02 / PREVIEW")
        layout = panel.layout()
        assert layout is not None
        self.preview = QLabel("等待第一帧")
        self.preview.setObjectName("preview")
        self.preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.preview.setMinimumHeight(280)
        self.preview.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        layout.addWidget(self.preview, 1)
        self.frame_count = QLabel("0 张")
        self.frame_count.setObjectName("countLabel")
        layout.addWidget(self.frame_count)
        self.thumbnails = QListWidget()
        self.thumbnails.setViewMode(QListWidget.ViewMode.IconMode)
        self.thumbnails.setIconSize(self._thumbnail_size())
        self.thumbnails.setFixedHeight(84)
        self.thumbnails.setSpacing(8)
        layout.addWidget(self.thumbnails)
        return panel

    def _build_render_panel(self) -> QWidget:
        panel = Panel("合成视频", "03 / OUTPUT")
        layout = panel.layout()
        assert layout is not None
        form = QFormLayout()
        form.setHorizontalSpacing(14)
        form.setVerticalSpacing(12)
        self.fps_combo = QComboBox()
        self.fps_combo.addItems(["24", "25", "30", "60"])
        form.addRow("输出帧率（FPS）", self.fps_combo)
        self.crf_spin = QSpinBox()
        self.crf_spin.setRange(0, 51)
        self.crf_spin.setValue(18)
        form.addRow("编码质量（CRF）", self.crf_spin)
        self.video_output = self._path_row(form, "视频输出路径", "output/timelapse.mp4", directory=False, save_file=True)
        layout.addLayout(form)
        self.overwrite = QCheckBox("允许覆盖已有视频")
        layout.addWidget(self.overwrite)
        self.render_button = QPushButton("▶  合成 MP4")
        self.render_button.setObjectName("secondaryButton")
        self.render_button.clicked.connect(self._start_render)
        layout.addWidget(self.render_button)
        self.output_label = QLabel("")
        self.output_label.setObjectName("successLabel")
        self.output_label.setWordWrap(True)
        layout.addWidget(self.output_label)
        return panel

    def _build_activity_panel(self) -> QWidget:
        panel = Panel("任务状态", "LIVE")
        layout = panel.layout()
        assert layout is not None
        self.progress = QProgressBar()
        self.progress.setTextVisible(False)
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        layout.addWidget(self.progress)
        self.activity = QLabel("就绪")
        self.activity.setObjectName("activityLabel")
        self.activity.setWordWrap(True)
        layout.addWidget(self.activity)
        self.error_label = QLabel("")
        self.error_label.setObjectName("errorLabel")
        self.error_label.setWordWrap(True)
        layout.addWidget(self.error_label)
        layout.addStretch()
        return panel

    def _path_row(self, form: QFormLayout, label: str, value: str, *, directory: bool, save_file: bool = False) -> QLineEdit:
        edit = QLineEdit(value)
        button = QPushButton("浏览…")
        button.setObjectName("smallButton")
        if directory:
            button.clicked.connect(lambda: self._choose_directory(edit))
        elif save_file:
            button.clicked.connect(lambda: self._choose_output(edit))
        row = QWidget()
        row_layout = QHBoxLayout(row)
        row_layout.setContentsMargins(0, 0, 0, 0)
        row_layout.setSpacing(8)
        row_layout.addWidget(edit, 1)
        row_layout.addWidget(button)
        form.addRow(label, row)
        return edit

    def _build_menu(self) -> None:
        file_menu = self.menuBar().addMenu("文件")
        exit_action = file_menu.addAction("退出")
        exit_action.triggered.connect(self.close)
        help_menu = self.menuBar().addMenu("帮助")
        about_action = help_menu.addAction("关于")
        about_action.triggered.connect(lambda: QMessageBox.about(self, "关于", "WHX 延时摄影自动化工具\nPyQt6 原生桌面客户端"))

    def _apply_style(self) -> None:
        self.setStyleSheet(
            """
            * { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; letter-spacing: 0; }
            QMainWindow { background: #11161d; color: #edf3f8; }
            #central { background: transparent; }
            QScrollArea, QScrollArea > QWidget > QWidget { background: transparent; }
            QMenuBar { background: rgba(13, 18, 24, 235); color: #c9d4de; padding: 4px 8px; }
            QMenuBar::item { padding: 5px 10px; border-radius: 6px; }
            QMenuBar::item:selected, QMenu { background: #202b36; }
            QMenu { color: #e7edf2; border: 1px solid #334352; padding: 6px; }
            QMenu::item { padding: 7px 28px 7px 10px; border-radius: 5px; }
            QMenu::item:selected { background: #2d80e5; }
            #eyebrow, #panelKicker { color: #7d91a4; font-size: 10px; font-weight: 700; }
            #windowTitle { color: #f4f8fb; font-size: 25px; font-weight: 700; }
            #statusBadge { color: #7ed6a0; background: rgba(43, 118, 75, 150); border: 1px solid #3c9c68; border-radius: 12px; padding: 7px 12px; }
            QGroupBox { background: rgba(20, 29, 38, 226); border: 1px solid #2e3e4d; border-radius: 12px; }
            #panelTitle { color: #f0f5f8; font-size: 17px; font-weight: 700; }
            QLabel { color: #dae4eb; }
            QFormLayout QLabel { color: #a9bac8; font-size: 12px; }
            QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox { background: rgba(10, 15, 20, 220); color: #eef4f7; border: 1px solid #3a4b5b; border-radius: 8px; padding: 8px 10px; min-height: 18px; selection-background-color: #2d80e5; }
            QLineEdit:focus, QComboBox:focus, QSpinBox:focus, QDoubleSpinBox:focus { border: 1px solid #4e9cf4; }
            QComboBox::drop-down { border: 0; width: 24px; }
            QComboBox QAbstractItemView { background: #1c2732; color: #eaf1f5; selection-background-color: #2d80e5; border: 1px solid #3b4f61; }
            QPushButton { color: #eef5f8; background: #273541; border: 1px solid #3c4e5e; border-radius: 8px; padding: 9px 14px; min-height: 18px; font-weight: 600; }
            QPushButton:hover { background: #334656; }
            QPushButton:pressed { background: #1e2a35; }
            QPushButton:disabled { color: #71808c; background: #202a33; border-color: #2a3742; }
            #primaryButton { background: #2d80e5; border-color: #4b9bf5; }
            #primaryButton:hover { background: #4290ed; }
            #secondaryButton { background: #167d82; border-color: #35a7a4; }
            #secondaryButton:hover { background: #219598; }
            #dangerButton { background: #6b3040; border-color: #a34a5e; }
            #dangerButton:hover { background: #80394c; }
            #smallButton { padding: 6px 10px; min-height: 16px; }
            #mutedLabel, #countLabel { color: #7f93a3; font-size: 11px; }
            #preview { background: rgba(5, 9, 13, 205); border: 1px solid #344756; border-radius: 8px; color: #7c8f9e; }
            QListWidget { background: transparent; border: 0; outline: 0; }
            QListWidget::item { background: #18232d; border: 1px solid #304250; border-radius: 6px; padding: 3px; }
            QCheckBox { color: #b9c9d5; spacing: 8px; }
            QCheckBox::indicator { width: 16px; height: 16px; border: 1px solid #526678; border-radius: 4px; background: #111a22; }
            QCheckBox::indicator:checked { background: #2d80e5; border-color: #55a1f2; }
            QProgressBar { background: #1a2630; border: 1px solid #334654; border-radius: 4px; height: 8px; }
            QProgressBar::chunk { background: #2d80e5; border-radius: 4px; }
            #activityLabel { color: #d9e4eb; font-size: 16px; font-weight: 600; }
            #errorLabel { color: #f39a9a; }
            #successLabel { color: #82d5a3; }
            QStatusBar { background: rgba(13, 18, 24, 235); color: #8fa2b1; }
            QSplitter::handle { background: transparent; }
            """
        )

    def paintEvent(self, event) -> None:  # type: ignore[no-untyped-def]
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        try:
            background = resource_path("timelapse/assets/background.jpg")
        except FileNotFoundError:
            background = None
        if background:
            pixmap = QPixmap(str(background))
            scaled = pixmap.scaled(self.size(), Qt.AspectRatioMode.KeepAspectRatioByExpanding, Qt.TransformationMode.SmoothTransformation)
            x = (self.width() - scaled.width()) // 2
            y = (self.height() - scaled.height()) // 2
            painter.setOpacity(0.2)
            painter.drawPixmap(x, y, scaled)
            painter.setOpacity(1.0)
        painter.fillRect(self.rect(), QColor(10, 15, 20, 188))
        super().paintEvent(event)

    def _thumbnail_size(self):
        return self._size(96, 58)

    @staticmethod
    def _size(width: int, height: int):
        from PyQt6.QtCore import QSize

        return QSize(width, height)

    def _update_stop_label(self) -> None:
        duration = self.stop_mode.currentData() == "duration"
        self.stop_value_label.setText("运行时长（分钟）" if duration else "目标图片数")
        self.stop_value.setValue(60 if duration else 360)

    def _choose_directory(self, edit: QLineEdit) -> None:
        path = QFileDialog.getExistingDirectory(self, "选择图片目录", edit.text() or str(Path.cwd()))
        if path:
            edit.setText(path)

    def _choose_output(self, edit: QLineEdit) -> None:
        path, _ = QFileDialog.getSaveFileName(self, "选择视频输出路径", edit.text() or "timelapse.mp4", "MP4 视频 (*.mp4)")
        if path:
            edit.setText(path)

    def _set_busy(self, busy: bool) -> None:
        self._busy = busy
        for widget in (self.start_button, self.render_button):
            widget.setEnabled(not busy)
        self.stop_button.setEnabled(busy)
        self.status_badge.setText("●  运行中" if busy else "●  就绪")
        self.status_badge.setObjectName("runningBadge" if busy else "statusBadge")
        self.status_badge.style().unpolish(self.status_badge)
        self.status_badge.style().polish(self.status_badge)

    def _start_capture(self) -> None:
        try:
            output_dir = Path(self.capture_dir.text().strip()).expanduser()
            config = CaptureConfig(
                rtsp_url=self.rtsp_edit.text().strip(),
                output_dir=output_dir,
                interval=self.interval_spin.value(),
                count=None if self.stop_mode.currentData() == "duration" else self.stop_value.value(),
                duration=self.stop_value.value() * 60 if self.stop_mode.currentData() == "duration" else None,
                ffmpeg_bin=self.ffmpeg_edit.text().strip() or _find_ffmpeg(),
                transport=self.transport.currentText(),
            )
            config.validate()
            output = Path(self.video_output.text().strip()).expanduser()
        except ValueError as exc:
            self._show_error(str(exc))
            return
        self._launch_worker("pipeline", config, output)

    def _start_render(self) -> None:
        input_dir = Path(self.capture_dir.text().strip()).expanduser()
        try:
            if not input_dir.is_dir():
                raise ValueError(f"输入目录不存在: {input_dir}")
            if not find_images(input_dir):
                raise ValueError(f"输入目录中没有可合成的图片: {input_dir}")
            config = CaptureConfig(rtsp_url="local", output_dir=input_dir, ffmpeg_bin=self.ffmpeg_edit.text().strip() or _find_ffmpeg())
            output = Path(self.video_output.text().strip()).expanduser()
        except ValueError as exc:
            self._show_error(str(exc))
            return
        self._launch_worker("render", config, output)

    def _launch_worker(self, kind: str, config: CaptureConfig, output: Path) -> None:
        if self._busy:
            return
        worker = JobWorker(
            kind,
            config=config,
            output=output,
            fps=float(self.fps_combo.currentText()),
            crf=self.crf_spin.value(),
            overwrite=self.overwrite.isChecked(),
        )
        thread = QThread(self)
        worker.moveToThread(thread)
        thread.started.connect(worker.run)
        worker.finished.connect(self._job_finished)
        worker.failed.connect(self._job_failed)
        worker.finished.connect(thread.quit)
        worker.failed.connect(thread.quit)
        thread.finished.connect(worker.deleteLater)
        thread.finished.connect(self._thread_finished)
        self._thread = thread
        self._worker = worker
        self._set_busy(True)
        self.progress.setValue(20 if kind == "pipeline" else 50)
        self.activity.setText("正在采集并自动合成视频…" if kind == "pipeline" else "正在合成视频…")
        self.error_label.clear()
        self.statusBar().showMessage("任务运行中")
        thread.start()

    def _stop_job(self) -> None:
        if self._worker:
            self._worker.stop()
            self.activity.setText("正在停止，已采集的图片将会保留…")
            self.statusBar().showMessage("正在停止任务")

    @pyqtSlot(object)
    def _job_finished(self, result) -> None:  # type: ignore[no-untyped-def]
        if isinstance(result, tuple):
            frames, output = result
            self._latest_frames = list(frames)
            self._refresh_preview()
            if output:
                self.output_label.setText(f"已生成：{output}")
                self.progress.setValue(100)
                self.activity.setText(f"已采集 {len(frames)} 张图片并完成视频合成")
            else:
                self.progress.setValue(100)
                self.activity.setText(f"已停止，保留 {len(frames)} 张图片")
        else:
            self.output_label.setText(f"已生成：{result}")
            self.progress.setValue(100)
            self.activity.setText("视频合成完成")
        self.statusBar().showMessage("任务完成")

    @pyqtSlot(str)
    def _job_failed(self, message: str) -> None:
        self.progress.setValue(0)
        self._show_error(message)
        self.activity.setText("任务失败")
        self.statusBar().showMessage("任务失败")

    def _thread_finished(self) -> None:
        self._set_busy(False)
        if self._thread:
            self._thread.deleteLater()
        self._thread = None
        self._worker = None

    def _refresh_preview(self) -> None:
        directory = Path(self.capture_dir.text().strip()).expanduser()
        frames = find_images(directory) if directory.is_dir() else []
        if frames != self._latest_frames:
            self._latest_frames = frames
            self.frame_count.setText(f"{len(frames)} 张")
            self.thumbnails.clear()
            for image in frames[-5:]:
                pixmap = QPixmap(str(image))
                item = QListWidgetItem(QIcon(pixmap), image.name)
                item.setToolTip(str(image))
                self.thumbnails.addItem(item)
            if frames:
                pixmap = QPixmap(str(frames[-1]))
                self.preview.setPixmap(pixmap.scaled(self.preview.size(), Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
                self.preview.setText("")

    def _show_error(self, message: str) -> None:
        self.error_label.setText(message)
        QMessageBox.warning(self, "操作失败", message)

    def closeEvent(self, event) -> None:  # type: ignore[no-untyped-def]
        if self._worker and self._busy:
            self._worker.stop()
            self._thread.quit() if self._thread else None
        event.accept()


def create_application() -> QApplication:
    app = QApplication.instance() or QApplication(sys.argv)
    app.setApplicationName("WHX 延时摄影自动化工具")
    app.setOrganizationName("WHX")
    return app


def main() -> int:
    app = create_application()
    window = TimelapseWindow()
    window.show()
    return app.exec()
