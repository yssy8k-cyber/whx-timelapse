"""主窗口关键按钮连接测试。"""

from __future__ import annotations

import logging
import tempfile
import unittest
from pathlib import Path

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication

from config.config_manager import ConfigManager
from config.config_manager import AppConfig
from ui.main_window import MainWindow


class MainWindowUiTests(unittest.TestCase):
    """验证 Dashboard 中的截图按钮可以真正启动和停止任务。"""

    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QApplication.instance() or QApplication([])

    def test_capture_buttons_start_and_stop_capture_controller(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            config_manager = ConfigManager(Path(directory) / "settings.json")
            window = MainWindow(
                config_manager,
                AppConfig(save_directory=directory),
                logging.getLogger("main-window-ui-test"),
            )
            window._connected = True
            window._set_capture_controls_enabled(True)
            window.directory_edit.setText(directory)

            window.start_button.click()
            self.assertTrue(window.capture_controller.is_running)
            window.stop_button.click()
            self.assertFalse(window.capture_controller.is_running)
            window.close()
            QTimer.singleShot(0, self.app.quit)
            self.app.processEvents()


if __name__ == "__main__":
    unittest.main()
