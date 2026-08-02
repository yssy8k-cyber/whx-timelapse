"""Timelapse Studio 主窗口。"""

from __future__ import annotations

import logging
from dataclasses import replace
from datetime import date
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFileDialog,
    QMainWindow,
    QMessageBox,
)

from camera.rtsp_camera import CameraController
from config.config_manager import AppConfig, ConfigManager
from log.logger import add_log_handler
from log.qt_log_handler import QtLogHandler
from ui.auto_video_controller import AutoVideoController
from ui.capture_controller import QtCaptureController
from ui.device_panel import DevicePanelMixin
from ui.panels import PanelMixin
from ui.style import apply_main_window_style
from ui.theme_toolbar import ThemeToolbar
from ui.video_controller import VideoController


class MainWindow(DevicePanelMixin, PanelMixin, QMainWindow):
    """第一阶段主窗口，负责界面状态和配置同步。"""

    def __init__(
        self,
        config_manager: ConfigManager,
        config: AppConfig,
        logger: logging.Logger,
    ) -> None:
        super().__init__()
        self.config_manager = config_manager
        self.config = config
        self.logger = logger
        self.theme_toolbar = ThemeToolbar(self)
        self.addToolBar(Qt.TopToolBarArea, self.theme_toolbar)
        self.camera = CameraController(self)
        self.capture_controller = QtCaptureController(self.camera.read_frame, self.logger, self)
        self.video_controller = VideoController(self.logger, self)
        self.auto_video_controller = AutoVideoController(self.logger, self)
        self._auto_video_active = False
        self.log_handler = QtLogHandler()
        self.log_handler.setFormatter(logging.Formatter("%(asctime)s | %(levelname)s | %(message)s"))
        add_log_handler(self.logger, self.log_handler)
        self._connected = False

        self.setWindowTitle("Timelapse Studio")
        self.resize(1180, 760)
        self.setMinimumSize(940, 620)
        self._build_ui()
        self.log_handler.message_emitted.connect(self.log_view.appendPlainText)
        self._load_config_into_ui()
        self._connect_signals()
        apply_main_window_style(self, self.config.dark_mode)
        if self.config.auto_generate_video:
            self.auto_video_controller.start()
        self.logger.info("Timelapse Studio 已启动")

    def _connect_signals(self) -> None:
        self._connect_device_panel_signals()
        self.connect_button.clicked.connect(self._connect_camera)
        self.disconnect_button.clicked.connect(self._disconnect_camera)
        self.browse_button.clicked.connect(self._choose_directory)
        self.theme_toolbar.theme_changed.connect(self._on_theme_changed)
        self.generate_button.clicked.connect(self._generate_video)
        self.auto_generate_check.stateChanged.connect(self._on_auto_generate_changed)
        self.interval_combo.currentIndexChanged.connect(self._on_interval_changed)
        self.camera.connection_succeeded.connect(self._on_connection_succeeded)
        self.camera.connection_failed.connect(self._on_connection_failed)
        self.camera.disconnected.connect(self._on_disconnected)
        self.capture_controller.capture_succeeded.connect(self._on_capture_succeeded)
        self.capture_controller.capture_failed.connect(self._on_capture_failed)
        self.video_controller.generated.connect(self._on_video_generated)
        self.video_controller.failed.connect(self._on_video_failed)
        self.auto_video_controller.generation_requested.connect(self._start_auto_video)

    def _load_config_into_ui(self) -> None:
        self._load_devices_into_ui()
        self.directory_edit.setText(self.config.save_directory)
        self.quality_spin.setValue(self.config.jpeg_quality)
        self.fps_combo.setCurrentText(f"{self.config.video_fps} FPS")
        self.delete_images_check.setChecked(self.config.delete_images_after_video)
        self.auto_generate_check.setChecked(self.config.auto_generate_video)
        self.theme_toolbar.set_dark_mode(self.config.dark_mode)
        self._set_interval_value(self.config.capture_interval)

    def _read_config_from_ui(self) -> AppConfig:
        self._save_current_device()
        return replace(
            self.config,
            rtsp_url=self.rtsp_edit.text().strip(),
            username=self.username_edit.text().strip(),
            password=self.password_edit.text(),
            save_directory=self.directory_edit.text().strip(),
            capture_interval=self._selected_interval_seconds(),
            jpeg_quality=self.quality_spin.value(),
            video_fps=int(self.fps_combo.currentText().split()[0]),
            delete_images_after_video=self.delete_images_check.isChecked(),
            auto_generate_video=self.auto_generate_check.isChecked(),
            dark_mode=self.theme_toolbar.is_dark_mode,
            devices=self.config.devices,
            active_device_index=self._active_device_index,
        )

    def _save_config(self) -> None:
        self.config = self._read_config_from_ui()
        if not self.config_manager.save(self.config):
            self.statusBar().showMessage("配置保存失败")
        else:
            self.logger.info("配置已保存")

    def _connect_camera(self) -> None:
        url = self.rtsp_edit.text().strip()
        if not url:
            QMessageBox.warning(self, "无法连接", "请先填写 RTSP 地址。")
            return
        self._save_config()
        self.connect_button.setEnabled(False)
        self.statusBar().showMessage("正在连接 RTSP...")
        self.logger.info("开始连接: %s", url)
        self.camera.connect_camera(url, self.username_edit.text(), self.password_edit.text())

    def _disconnect_camera(self) -> None:
        self._stop_capture()
        self.camera.disconnect_camera()
        self.statusBar().showMessage("正在断开...")

    def _on_connection_succeeded(self, url: str) -> None:
        self._connected = True
        self.connect_button.setEnabled(False)
        self.disconnect_button.setEnabled(True)
        self.interval_combo.setEnabled(True)
        self.custom_interval_spin.setEnabled(self.interval_combo.currentText() == "自定义")
        self.quality_spin.setEnabled(True)
        self.start_button.setEnabled(True)
        self.statusBar().showMessage("已连接")
        self.logger.info("连接测试成功: %s", url)

    def _on_connection_failed(self, message: str) -> None:
        self._connected = False
        self._stop_capture()
        self.connect_button.setEnabled(True)
        self.disconnect_button.setEnabled(False)
        self._set_capture_controls_enabled(False)
        self.statusBar().showMessage("连接失败")
        self.logger.error("连接失败: %s", message)
        QMessageBox.warning(self, "连接失败", message)

    def _on_disconnected(self) -> None:
        self._connected = False
        self._stop_capture()
        self.connect_button.setEnabled(True)
        self.disconnect_button.setEnabled(False)
        self._set_capture_controls_enabled(False)
        self.statusBar().showMessage("已断开")
        self.logger.info("摄像头已断开")

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

    def _on_auto_generate_changed(self, state: int) -> None:
        """保存自动任务开关，并启动或停止调度线程。"""
        enabled = bool(state)
        self._save_config()
        if enabled:
            self.auto_video_controller.start()
            self.statusBar().showMessage("每日自动生成已启用")
        else:
            self.auto_video_controller.stop()
            self.statusBar().showMessage("每日自动生成已停用")

    def _on_theme_changed(self, dark_mode: bool) -> None:
        apply_main_window_style(self, dark_mode)
        self._save_config()
        self.statusBar().showMessage("已切换到深色主题" if dark_mode else "已切换到浅色主题")

    def _start_auto_video(self, date_text: str) -> None:
        """在 GUI 主线程中响应调度器信号。"""
        if not self.auto_generate_check.isChecked():
            return
        image_directory = Path(self.directory_edit.text().strip()) / date_text
        self._start_video_generation(image_directory, automatic=True)

    def _generate_video(self) -> None:
        """异步生成今天的日期目录视频。"""
        image_directory = Path(self.directory_edit.text().strip()) / date.today().isoformat()
        self._start_video_generation(image_directory, automatic=False)

    def _start_video_generation(self, image_directory: Path, automatic: bool) -> None:
        fps = int(self.fps_combo.currentText().split()[0])
        self._auto_video_active = automatic
        started = self.video_controller.start(
            image_directory,
            fps,
            self.delete_images_check.isChecked(),
        )
        if started:
            self.generate_button.setEnabled(False)
            message = "正在自动生成视频..." if automatic else "正在生成视频..."
            self.statusBar().showMessage(message)
        else:
            self._auto_video_active = False
            self.logger.warning("视频生成任务正在运行，忽略新的生成请求")

    def _on_video_generated(self, output_path: str) -> None:
        automatic = self._auto_video_active
        self._auto_video_active = False
        self.generate_button.setEnabled(True)
        prefix = "自动视频生成成功" if automatic else "视频生成成功"
        self.statusBar().showMessage(f"{prefix}: {output_path}")

    def _on_video_failed(self, message: str) -> None:
        automatic = self._auto_video_active
        self._auto_video_active = False
        self.generate_button.setEnabled(True)
        self.statusBar().showMessage("视频生成失败")
        if automatic:
            self.logger.error("自动视频生成失败: %s", message)
        else:
            QMessageBox.warning(self, "视频生成失败", message)

    def _choose_directory(self) -> None:
        current = self.directory_edit.text().strip() or str(Path.home())
        directory = QFileDialog.getExistingDirectory(self, "选择图片保存目录", current)
        if directory:
            self.directory_edit.setText(directory)
            self._save_config()

    def closeEvent(self, event) -> None:  # noqa: N802 - Qt API 名称
        self._save_config()
        self.auto_video_controller.stop()
        self._stop_capture()
        self.video_controller.shutdown()
        self.camera.shutdown()
        self.logger.info("Timelapse Studio 已退出")
        super().closeEvent(event)
