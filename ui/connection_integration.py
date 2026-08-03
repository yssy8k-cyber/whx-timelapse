"""将 RTSP 主连接生命周期接入主窗口。"""

from __future__ import annotations

from PySide6.QtWidgets import QMessageBox


class ConnectionIntegrationMixin:
    """处理主截图 RTSP 连接，并在成功后启动独立预览。"""

    def _connect_camera(self) -> None:
        """异步测试主 RTSP 连接。"""
        url = self.rtsp_edit.text().strip()
        if not url:
            QMessageBox.warning(self, "无法连接", "请先填写 RTSP 地址。")
            return
        self._save_config()
        self.connect_button.setEnabled(False)
        self.statusBar().showMessage("正在连接 RTSP...")
        self.logger.info("开始连接: %s", url)
        self.camera.connect_camera(
            url,
            self.username_edit.text(),
            self.password_edit.text(),
        )

    def _disconnect_camera(self) -> None:
        """停止截图和预览，再释放主 RTSP 连接。"""
        self._stop_capture()
        self._stop_preview()
        self.camera.disconnect_camera()
        self.preview_panel.show_not_connected()
        self.statusBar().showMessage("正在断开...")

    def _on_connection_succeeded(self, url: str) -> None:
        """主 RTSP 成功后立即启动独立实时预览。"""
        self._connected = True
        self.connect_button.setEnabled(False)
        self.disconnect_button.setEnabled(True)
        self.interval_combo.setEnabled(True)
        self.custom_interval_spin.setEnabled(self.interval_combo.currentText() == "自定义")
        self.quality_spin.setEnabled(True)
        self.start_button.setEnabled(True)
        self.preview_panel.show_connecting()
        self.preview_controller.start(
            self.rtsp_edit.text().strip(),
            self.username_edit.text(),
            self.password_edit.text(),
        )
        self.statusBar().showMessage("已连接")
        self.logger.info("连接测试成功: %s", url)

    def _on_connection_failed(self, message: str) -> None:
        """主 RTSP 失败时停止相关任务并显示失败状态。"""
        self._connected = False
        self._stop_capture()
        self._stop_preview()
        self.connect_button.setEnabled(True)
        self.disconnect_button.setEnabled(False)
        self._set_capture_controls_enabled(False)
        self.preview_panel.show_connection_failed()
        self.statusBar().showMessage("连接失败")
        self.logger.error("连接失败: %s", message)
        QMessageBox.warning(self, "连接失败", message)

    def _on_disconnected(self) -> None:
        """主 RTSP 断开后同步清理预览和截图状态。"""
        self._connected = False
        self._stop_capture()
        self._stop_preview()
        self.connect_button.setEnabled(True)
        self.disconnect_button.setEnabled(False)
        self._set_capture_controls_enabled(False)
        self.preview_panel.show_not_connected()
        self.statusBar().showMessage("已断开")
        self.logger.info("摄像头已断开")


__all__ = ["ConnectionIntegrationMixin"]
