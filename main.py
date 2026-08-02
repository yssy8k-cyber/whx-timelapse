"""Timelapse Studio 应用入口。"""

from __future__ import annotations

import sys

from PySide6.QtWidgets import QApplication

from config.config_manager import ConfigManager
from log.logger import configure_logging, shutdown_logging
from ui.main_window import MainWindow


def main() -> int:
    """创建 Qt 应用并启动主窗口。"""
    app = QApplication(sys.argv)
    app.setApplicationName("Timelapse Studio")
    app.setOrganizationName("Timelapse Studio")

    config_manager = ConfigManager()
    config = config_manager.load()
    logger = configure_logging(config_manager.log_dir)

    window = MainWindow(
        config_manager=config_manager,
        config=config,
        logger=logger,
    )
    window.show()
    exit_code = app.exec()
    shutdown_logging(logger)
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
