"""主窗口的界面面板构建。"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QPushButton,
    QPlainTextEdit,
    QSpinBox,
    QSplitter,
    QStatusBar,
    QVBoxLayout,
    QWidget,
)


class PanelMixin:
    """集中构建主窗口面板，避免主窗口承担布局细节。"""

    def _build_ui(self) -> None:
        self.setStatusBar(QStatusBar(self))
        self.statusBar().showMessage("就绪")

        central = QWidget()
        root_layout = QVBoxLayout(central)
        root_layout.setContentsMargins(20, 18, 20, 16)
        root_layout.setSpacing(14)

        title = QLabel("Timelapse Studio")
        title.setObjectName("titleLabel")
        subtitle = QLabel("海康威视 RTSP 长期延时摄影工具")
        subtitle.setObjectName("subtitleLabel")
        root_layout.addWidget(title)
        root_layout.addWidget(subtitle)

        splitter = QSplitter(Qt.Horizontal)
        splitter.setChildrenCollapsible(False)
        splitter.addWidget(self._build_device_panel())
        splitter.addWidget(self._build_workspace_panel())
        splitter.setSizes([250, 850])
        root_layout.addWidget(splitter, 1)
        self.setCentralWidget(central)

    def _build_device_panel(self) -> QWidget:
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 8, 0)
        heading = QLabel("设备")
        heading.setObjectName("sectionLabel")
        layout.addWidget(heading)

        self.device_list = QListWidget()
        self.device_list.addItem("海康威视摄像头 1")
        self.device_list.setCurrentRow(0)
        layout.addWidget(self.device_list, 1)

        device_buttons = QHBoxLayout()
        self.add_device_button = QPushButton("＋ 添加设备")
        self.remove_device_button = QPushButton("删除")
        self.remove_device_button.setEnabled(False)
        device_buttons.addWidget(self.add_device_button)
        device_buttons.addWidget(self.remove_device_button)
        layout.addLayout(device_buttons)
        return panel

    def _build_workspace_panel(self) -> QWidget:
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(8, 0, 0, 0)
        layout.setSpacing(12)

        layout.addWidget(self._build_connection_group())
        layout.addWidget(self._build_capture_group())
        layout.addWidget(self._build_storage_group())
        layout.addWidget(self._build_log_group(), 1)

        actions = QHBoxLayout()
        self.start_button = QPushButton("▶  开始截图")
        self.stop_button = QPushButton("■  停止")
        self.generate_button = QPushButton("生成视频")
        self.start_button.setEnabled(False)
        self.stop_button.setEnabled(False)
        self.generate_button.setEnabled(True)
        self.start_button.clicked.connect(self._start_capture)
        self.stop_button.clicked.connect(self._stop_capture)
        actions.addWidget(self.start_button)
        actions.addWidget(self.stop_button)
        actions.addStretch()
        actions.addWidget(self.generate_button)
        layout.addLayout(actions)
        return panel

    def _build_connection_group(self) -> QGroupBox:
        group = QGroupBox("连接")
        layout = QFormLayout(group)
        self.rtsp_edit = QLineEdit()
        self.rtsp_edit.setPlaceholderText("例如 rtsp://192.168.1.64:554/Streaming/Channels/101")
        self.username_edit = QLineEdit()
        self.password_edit = QLineEdit()
        self.password_edit.setEchoMode(QLineEdit.Password)
        self.connect_button = QPushButton("连接测试")
        self.disconnect_button = QPushButton("断开")
        self.disconnect_button.setEnabled(False)
        connection_buttons = QHBoxLayout()
        connection_buttons.addWidget(self.connect_button)
        connection_buttons.addWidget(self.disconnect_button)
        layout.addRow("RTSP 地址", self.rtsp_edit)
        layout.addRow("用户名", self.username_edit)
        layout.addRow("密码", self.password_edit)
        layout.addRow("操作", connection_buttons)
        return group

    def _build_capture_group(self) -> QGroupBox:
        group = QGroupBox("截图设置")
        layout = QFormLayout(group)
        self.interval_combo = QComboBox()
        self.interval_combo.addItems(["5 秒", "10 秒", "15 秒", "30 秒", "60 秒", "自定义"])
        self.custom_interval_spin = QSpinBox()
        self.custom_interval_spin.setRange(1, 86400)
        self.custom_interval_spin.setValue(60)
        self.custom_interval_spin.setSuffix(" 秒")
        self.quality_spin = QSpinBox()
        self.quality_spin.setRange(1, 100)
        self.quality_spin.setSuffix(" %")
        self.interval_combo.setEnabled(False)
        self.custom_interval_spin.setEnabled(False)
        self.quality_spin.setEnabled(False)
        layout.addRow("截图间隔", self.interval_combo)
        layout.addRow("自定义间隔", self.custom_interval_spin)
        layout.addRow("JPEG 质量", self.quality_spin)
        return group

    def _build_storage_group(self) -> QGroupBox:
        group = QGroupBox("保存与视频")
        layout = QFormLayout(group)
        directory_layout = QHBoxLayout()
        self.directory_edit = QLineEdit()
        self.browse_button = QPushButton("浏览")
        directory_layout.addWidget(self.directory_edit)
        directory_layout.addWidget(self.browse_button)
        self.fps_combo = QComboBox()
        self.fps_combo.addItems(["15 FPS", "24 FPS", "30 FPS", "60 FPS"])
        self.delete_images_check = QCheckBox("生成成功后删除图片")
        self.auto_generate_check = QCheckBox("每日 00:00 自动生成昨日视频")
        self.fps_combo.setEnabled(True)
        self.delete_images_check.setEnabled(True)
        self.auto_generate_check.setEnabled(True)
        layout.addRow("图片目录", directory_layout)
        layout.addRow("视频帧率", self.fps_combo)
        layout.addRow("清理策略", self.delete_images_check)
        layout.addRow("自动任务", self.auto_generate_check)
        return group

    def _build_log_group(self) -> QGroupBox:
        group = QGroupBox("日志")
        layout = QVBoxLayout(group)
        self.log_view = QPlainTextEdit()
        self.log_view.setReadOnly(True)
        self.log_view.setPlaceholderText("连接状态和运行日志会显示在这里")
        layout.addWidget(self.log_view)
        return group

    def _on_capture_succeeded(self, image_path: str) -> None:
        self.statusBar().showMessage(f"最近截图: {image_path}")

    def _on_capture_failed(self, message: str) -> None:
        self.statusBar().showMessage(f"截图失败: {message}")
