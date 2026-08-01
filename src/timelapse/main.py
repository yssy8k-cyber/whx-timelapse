"""Crash-reporting entry point for the native PyQt6 desktop client."""

from __future__ import annotations

import os
import sys
import tempfile
import traceback
from pathlib import Path


def _configure_qt_plugins() -> None:
    """Make the bundled Cocoa/Windows Qt platform plugins explicit."""

    meipass = getattr(sys, "_MEIPASS", None)
    if not meipass:
        return
    root = Path(meipass)
    plugin_candidates = [
        root / "PyQt6" / "Qt6" / "plugins",
        root.parent / "Resources" / "PyQt6" / "Qt6" / "plugins",
        root.parent / "Frameworks" / "PyQt6" / "Qt6" / "plugins",
    ]
    for plugin_dir in plugin_candidates:
        if (plugin_dir / "platforms").is_dir():
            os.environ.setdefault("QT_PLUGIN_PATH", str(plugin_dir))
            os.environ.setdefault("QT_QPA_PLATFORM_PLUGIN_PATH", str(plugin_dir / "platforms"))
            return


def _crash_log_path() -> Path:
    candidates = [
        Path.home() / "Library" / "Logs" / "WHXTimelapse" / "startup.log",
        Path.home() / "AppData" / "Local" / "WHXTimelapse" / "startup.log",
        Path(tempfile.gettempdir()) / "WHXTimelapse-startup.log",
    ]
    for candidate in candidates:
        try:
            candidate.parent.mkdir(parents=True, exist_ok=True)
            return candidate
        except OSError:
            continue
    return candidates[-1]


def _report_startup_error(error: BaseException) -> None:
    details = "".join(traceback.format_exception(type(error), error, error.__traceback__))
    log_path = _crash_log_path()
    try:
        log_path.write_text(details, encoding="utf-8")
    except OSError:
        pass

    try:
        from PyQt6.QtWidgets import QApplication, QMessageBox

        app = QApplication.instance() or QApplication(sys.argv)
        QMessageBox.critical(
            None,
            "WHX 延时摄影自动化工具启动失败",
            f"程序启动失败，详细日志已保存到：\n{log_path}\n\n{error}",
        )
        app.quit()
    except Exception:
        # Import or platform-plugin failures can happen before Qt can show a dialog.
        pass


def main() -> int:
    try:
        _configure_qt_plugins()
        from timelapse.main_window import TimelapseWindow, create_application

        app = create_application()
        window = TimelapseWindow()
        window.show()
        return app.exec()
    except BaseException as error:
        _report_startup_error(error)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
