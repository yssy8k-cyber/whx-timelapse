"""Timelapse Studio 主窗口。"""

from __future__ import annotations

import logging
from dataclasses import replace
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QMainWindow,
    QMessageBox,
)

from camera.rtsp_camera import CameraController
from camera.preview_controller import PreviewController
from config.config_manager import AppConfig, ConfigManager
from database import SQLiteDatabase
from log.logger import add_log_handler
from log.qt_log_handler import QtLogHandler
from ui.auto_video_controller import AutoVideoController
from ui.capture_controller import QtCaptureController
from ui.connection_integration import ConnectionIntegrationMixin
from ui.device_panel import DevicePanelMixin
from ui.panels import PanelMixin
from ui.preview_integration import PreviewIntegrationMixin
from ui.video_plan_integration import VideoPlanIntegrationMixin
from ui.style import apply_main_window_style
from ui.theme_toolbar import ThemeToolbar
from ui.video_controller import VideoController


class MainWindow(
    DevicePanelMixin,
    ConnectionIntegrationMixin,
    PreviewIntegrationMixin,
    VideoPlanIntegrationMixin,
    PanelMixin,
    QMainWindow,
):
    """第一阶段主窗口，负责界面状态和配置同步。"""

    def __init__(
        self,
        config_manager: ConfigManager,
        config: AppConfig,
        logger: logging.Logger,
        database: SQLiteDatabase | None = None,
    ) -> None:
        super().__init__()
        self.config_manager = config_manager
        self.config = config
        self.logger = logger
        self.database = database
        self.theme_toolbar = ThemeToolbar(self)
        self.addToolBar(Qt.TopToolBarArea, self.theme_toolbar)
        self.camera = CameraController(self)
        self.preview_controller = PreviewController(self.logger, self)
        self.capture_controller = QtCaptureController(self.camera.read_frame, self.logger, self)
        self.video_controller = VideoController(self.logger, self)
        self.auto_video_controller = AutoVideoController(self.logger, self)
        self._auto_video_active = False
        self.log_handler = QtLogHandler()
        self.log_handler.setFormatter(logging.Formatter("%(asctime)s | %(levelname)s | %(message)s"))
        add_log_handler(self.logger, self.log_handler)
        self._connected = False

        self.setWindowTitle("海康威视延时摄影系统 · Hikvision Time-Lapse Client")
        self.resize(1180, 980)
        self.setMinimumSize(940, 760)
        self._build_ui()
        self.log_handler.message_emitted.connect(self._append_log_message)
        self._load_config_into_ui()
        self._connect_signals()
        apply_main_window_style(self, self.config.dark_mode)
        if self.config.schedule_mode != "manual":
            self._start_generation_schedule()
        self.logger.info("Timelapse Studio 已启动")

    def _connect_signals(self) -> None:
        self._connect_device_panel_signals()
        self.connect_button.clicked.connect(self._connect_camera)
        self.disconnect_button.clicked.connect(self._disconnect_camera)
        self.browse_button.clicked.connect(self._choose_directory)
        self.theme_toolbar.theme_changed.connect(self._on_theme_changed)
        self.start_button.clicked.connect(self._start_capture)
        self.stop_button.clicked.connect(self._stop_capture)
        self.generate_button.clicked.connect(self._generate_video)
        self.interval_combo.currentIndexChanged.connect(self._on_interval_changed)
        self.camera.connection_succeeded.connect(self._on_connection_succeeded)
        self.camera.connection_failed.connect(self._on_connection_failed)
        self.camera.disconnected.connect(self._on_disconnected)
        self.camera.connection_succeeded.connect(lambda _url: self._set_dashboard_camera_state("已连接"))
        self.camera.connection_failed.connect(lambda _message: self._set_dashboard_camera_state("连接失败"))
        self.camera.disconnected.connect(lambda: self._set_dashboard_camera_state("未连接"))
        self.video_browse_button.clicked.connect(self._choose_video_directory)
        self.open_video_directory_button.clicked.connect(self._open_video_directory)
        self.schedule_mode_combo.currentIndexChanged.connect(self._on_schedule_changed)
        self.schedule_interval_combo.currentIndexChanged.connect(
            self._on_schedule_interval_changed
        )
        self.range_combo.currentIndexChanged.connect(self._on_range_changed)
        self.preview_panel.refresh_button.clicked.connect(self._refresh_preview)
        self.preview_controller.connected.connect(self._on_preview_connected)
        self.preview_controller.frame_ready.connect(self._on_preview_frame_available)
        self.preview_controller.error.connect(self._on_preview_error)
        self.capture_controller.running_changed.connect(self._on_capture_running_changed)
        self.capture_controller.running_changed.connect(
            lambda running: self._set_dashboard_capture_state("运行中" if running else "未运行")
        )
        self.capture_controller.capture_succeeded.connect(self._on_capture_succeeded)
        self.capture_controller.capture_failed.connect(self._on_capture_failed)
        self.video_controller.generated.connect(self._on_video_generated)
        self.video_controller.failed.connect(self._on_video_failed)
        self.video_controller.progress.connect(self._on_video_progress)
        self.video_controller.generated.connect(lambda _path: self._set_dashboard_video_state("已完成"))
        self.video_controller.failed.connect(lambda _message: self._set_dashboard_video_state("生成失败"))
        self.auto_video_controller.generation_requested.connect(self._start_auto_video)

    def _load_config_into_ui(self) -> None:
        self._load_devices_into_ui()
        self._load_video_config_into_ui()
        self.theme_toolbar.set_dark_mode(self.config.dark_mode)
        self._set_interval_value(self.config.capture_interval)

    def _read_config_from_ui(self) -> AppConfig:
        self._save_current_device()
        return replace(
            self.config,
            **self._read_video_config_fields(),
            rtsp_url=self.rtsp_edit.text().strip(),
            username=self.username_edit.text().strip(),
            password=self.password_edit.text(),
            capture_interval=self._selected_interval_seconds(),
            dark_mode=self.theme_toolbar.is_dark_mode,
            devices=self.config.devices,
            active_device_index=self._active_device_index,
        )

    def _save_config(self) -> None:
        self.config = self._read_config_from_ui()
        if not self.config_manager.save(self.config):
            self.statusBar().showMessage("配置保存失败")
        else:
            if self.database is not None:
                try:
                    self.database.replace_cameras(self.config.devices)
                    self.database.save_app_config(
                        {
                            "capture_interval": self.config.capture_interval,
                            "save_directory": self.config.save_directory,
                            "video_output_directory": self.config.video_output_directory,
                            "video_fps": self.config.video_fps,
                            "dark_mode": self.config.dark_mode,
                        }
                    )
                except Exception as error:
                    self.logger.exception("SQLite 配置保存失败: %s", error)
            self.logger.info("配置已保存")

    def _selected_interval_seconds(self) -> int:
        """读取当前预设或自定义截图间隔。"""
        preset_seconds = {"5 秒": 5, "10 秒": 10, "15 秒": 15, "30 秒": 30, "60 秒": 60}
        return preset_seconds.get(self.interval_combo.currentText(), self.custom_interval_spin.value())

    def _set_interval_value(self, seconds: int) -> None:
        """将配置中的间隔恢复到界面控件。"""
        preset_seconds = {5: "5 秒", 10: "10 秒", 15: "15 秒", 30: "30 秒", 60: "60 秒"}
        if seconds in preset_seconds:
            self.interval_combo.setCurrentText(preset_seconds[seconds])
        else:
            self.interval_combo.setCurrentText("自定义")
            self.custom_interval_spin.setValue(max(1, seconds))

    def _on_interval_changed(self) -> None:
        self.custom_interval_spin.setEnabled(
            self._connected and self.interval_combo.currentText() == "自定义"
        )

    def _set_capture_controls_enabled(self, enabled: bool) -> None:
        self.interval_combo.setEnabled(enabled)
        self.custom_interval_spin.setEnabled(
            enabled and self.interval_combo.currentText() == "自定义"
        )
        self.quality_spin.setEnabled(enabled)
        self.start_button.setEnabled(enabled and not self.capture_controller.is_running)
        self.stop_button.setEnabled(enabled and self.capture_controller.is_running)

    def _start_capture(self) -> None:
        if not self._connected:
            return
        self._save_config()
        try:
            started = self.capture_controller.start(
                self._selected_interval_seconds(),
                self.quality_spin.value(),
                Path(self.directory_edit.text().strip()),
            )
        except (OSError, ValueError) as error:
            self.logger.error("启动截图失败: %s", error)
            QMessageBox.warning(self, "无法开始截图", str(error))
            return
        if started:
            self._set_capture_controls_enabled(True)
            self.statusBar().showMessage("截图运行中")

    def _stop_capture(self) -> None:
        was_running = self.capture_controller.is_running
        stopped = self.capture_controller.stop()
        if not stopped:
            self.statusBar().showMessage("截图线程停止超时")
            return
        self._set_capture_controls_enabled(self._connected)
        if was_running:
            self.statusBar().showMessage("截图已停止")

    def _on_theme_changed(self, dark_mode: bool) -> None:
        apply_main_window_style(self, dark_mode)
        self._save_config()
        self.statusBar().showMessage("已切换到深色主题" if dark_mode else "已切换到浅色主题")

    def _append_log_message(self, message: str) -> None:
        """将日志同步到日志页和首页摘要。"""
        self.log_view.appendPlainText(message)
        self.home_log_view.appendPlainText(message)

    def _set_dashboard_camera_state(self, state: str) -> None:
        """更新首页和侧栏的摄像头状态，不参与连接控制。"""
        self.camera_metric.value_label.setText(state)
        self.sidebar_connection_label.setText(f"● {state}")
        self.header_status.setText(f"● {state}")

    def _set_dashboard_capture_state(self, state: str) -> None:
        """更新首页截图状态摘要。"""
        self.capture_metric.value_label.setText(state)

    def _set_dashboard_video_state(self, state: str) -> None:
        """更新首页视频状态摘要。"""
        self.video_metric.value_label.setText(state)

    def closeEvent(self, event) -> None:  # noqa: N802 - Qt API 名称
        self._save_config()
        self.auto_video_controller.stop()
        self._stop_capture()
        self.video_controller.shutdown()
        self.preview_controller.shutdown()
        self.camera.shutdown()
        self.logger.info("Timelapse Studio 已退出")
        super().closeEvent(event)
