"""将实时预览控制器接入主窗口生命周期。"""

from __future__ import annotations

from camera.preview_controller import stream_type_from_url


class PreviewIntegrationMixin:
    """集中处理预览、截图状态和设备切换之间的界面协作。"""

    def _on_capture_running_changed(self, running: bool) -> None:
        """根据截图线程状态显示或隐藏预览上的 REC 标识。"""
        self.preview_panel.set_recording(running)

    def _on_preview_connected(self) -> None:
        """预览流连接成功后更新码流状态。"""
        if not self._connected:
            return
        stream_type = stream_type_from_url(self.rtsp_edit.text())
        self.preview_panel.show_connected(stream_type)
        self.logger.info("实时预览已连接，码流类型: %s", stream_type)

    def _on_preview_error(self, message: str) -> None:
        """显示预览错误；主 RTSP 截图连接仍可独立保持。"""
        self.logger.error("实时预览失败: %s", message)
        self.preview_panel.show_connection_failed()

    def _on_preview_frame_available(self) -> None:
        """在 GUI 线程中消费单槽缓冲区中的最新画面。"""
        frame = self.preview_controller.take_latest_frame()
        if frame is not None:
            self.preview_panel.update_frame(*frame)

    def _refresh_preview(self) -> None:
        """只重建预览流，不停止正在运行的截图任务。"""
        if not self._connected:
            self.preview_panel.show_not_connected()
            return
        self.preview_panel.show_connecting()
        self.preview_controller.start(
            self.rtsp_edit.text().strip(),
            self.username_edit.text(),
            self.password_edit.text(),
        )

    def _stop_preview(self) -> None:
        """停止预览并等待其线程释放 VideoCapture。"""
        if not self.preview_controller.stop():
            self.logger.warning("实时预览线程未能在超时内停止")

    def _handle_device_switch(self) -> None:
        """切换设备前停止旧设备的截图、预览和 RTSP 连接。"""
        if not self._connected and not self.preview_controller.is_running:
            return
        self._connected = False
        self._stop_capture()
        self._stop_preview()
        self.camera.disconnect_camera()
        self.preview_panel.show_not_connected()
        self.statusBar().showMessage("设备已切换，请重新连接")


__all__ = ["PreviewIntegrationMixin"]
