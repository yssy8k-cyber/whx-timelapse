"""Timelapse Studio 应用入口。"""

from __future__ import annotations

import sys

from PySide6.QtWidgets import QApplication

from config.config_manager import ConfigManager
from database import SQLiteDatabase
from log.logger import configure_logging, shutdown_logging
from ui.main_window import MainWindow


def main() -> int:
    """创建 Qt 应用并启动主窗口。"""
    app = QApplication(sys.argv)
    app.setApplicationName("Hikvision Time-Lapse Client")
    app.setOrganizationName("Hikvision Time-Lapse Client")

    config_manager = ConfigManager()
    config = config_manager.load()
    logger = configure_logging(config_manager.log_dir)
    database = SQLiteDatabase(config_manager.database_path)
    try:
        database.initialize()
    except OSError as error:
        logger.exception("SQLite 初始化失败，继续使用 JSON 配置: %s", error)
        database = None

    window = MainWindow(
        config_manager=config_manager,
        config=config,
        logger=logger,
        database=database,
    )
    window.show()
    exit_code = app.exec()
    shutdown_logging(logger)
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
