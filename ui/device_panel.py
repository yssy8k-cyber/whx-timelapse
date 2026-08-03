"""设备列表与设备连接配置的界面逻辑。"""

from __future__ import annotations

from dataclasses import replace

from PySide6.QtWidgets import QInputDialog, QMessageBox

from config.device_config import DeviceConfig


class DevicePanelMixin:
    """管理左侧设备列表和右侧当前设备配置。"""

    def _connect_device_panel_signals(self) -> None:
        self.device_list.currentRowChanged.connect(self._on_device_changed)
        self.add_device_button.clicked.connect(self._add_device)
        self.remove_device_button.clicked.connect(self._remove_device)

    def _load_devices_into_ui(self) -> None:
        self.device_list.clear()
        if not self.config.devices:
            self.config.devices.append(DeviceConfig())
        for device in self.config.devices:
            self.device_list.addItem(device.name)
        index = max(0, min(self.config.active_device_index, len(self.config.devices) - 1))
        self._active_device_index = index
        self.device_list.setCurrentRow(index)
        self._load_active_device()

    def _load_active_device(self) -> None:
        device = self.config.devices[self._active_device_index]
        self.rtsp_edit.setText(device.rtsp_url)
        self.username_edit.setText(device.username)
        self.password_edit.setText(device.password)
        sidebar_label = getattr(self, "sidebar_device_label", None)
        if sidebar_label is not None:
            sidebar_label.setText(device.name)

    def _save_current_device(self) -> None:
        """把右侧编辑框保存回当前设备对象。"""
        row = self._active_device_index
        if row < 0 or row >= len(self.config.devices):
            return
        current = self.config.devices[row]
        self.config.devices[row] = replace(
            current,
            rtsp_url=self.rtsp_edit.text().strip(),
            username=self.username_edit.text().strip(),
            password=self.password_edit.text(),
        )

    def _on_device_changed(self, row: int) -> None:
        if row < 0 or row >= len(self.config.devices):
            return
        device_switch_handler = getattr(self, "_handle_device_switch", None)
        if device_switch_handler is not None:
            device_switch_handler()
        self._save_current_device()
        self._active_device_index = row
        self.config.active_device_index = row
        self._load_active_device()
        self._save_config()

    def _add_device(self) -> None:
        name, accepted = QInputDialog.getText(
            self,
            "添加设备",
            "设备名称:",
            text=f"摄像头 {len(self.config.devices) + 1}",
        )
        if not accepted or not name.strip():
            return
        self._save_current_device()
        self.config.devices.append(DeviceConfig(name=name.strip()))
        self.device_list.addItem(name.strip())
        self.device_list.setCurrentRow(len(self.config.devices) - 1)
        self._save_config()

    def _remove_device(self) -> None:
        if len(self.config.devices) <= 1:
            QMessageBox.information(self, "无法删除", "至少需要保留一个设备。")
            return
        row = self.device_list.currentRow()
        if row < 0:
            return
        name = self.config.devices[row].name
        answer = QMessageBox.question(
            self,
            "删除设备",
            f"确定删除设备“{name}”吗？",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if answer != QMessageBox.Yes:
            return
        self._save_current_device()
        self.config.devices.pop(row)
        self.device_list.takeItem(row)
        new_row = min(row, len(self.config.devices) - 1)
        self.device_list.setCurrentRow(new_row)
        self._save_config()
