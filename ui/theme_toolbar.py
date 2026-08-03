"""顶部主题切换工具栏。"""

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtGui import QPalette
from PySide6.QtWidgets import QApplication, QComboBox, QLabel, QToolBar


class ThemeToolbar(QToolBar):
    """提供浅色、深色和跟随系统三种主题选择。"""

    theme_changed = Signal(bool)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("themeToolbar")
        self.setMovable(False)
        self.setFloatable(False)
        self.addWidget(QLabel("外观"))
        self.mode_combo = QComboBox()
        self.mode_combo.addItems(["浅色", "深色", "跟随系统"])
        self.mode_combo.currentIndexChanged.connect(self._on_mode_changed)
        self.addWidget(self.mode_combo)

    @property
    def is_dark_mode(self) -> bool:
        """返回当前是否为深色主题。"""
        if self.mode_combo.currentIndex() == 2:
            palette = QApplication.palette()
            return palette.color(QPalette.Window).lightness() < 128
        return self.mode_combo.currentIndex() == 1

    def set_dark_mode(self, enabled: bool) -> None:
        """恢复主题配置而不重复发出切换信号。"""
        previous_state = self.mode_combo.blockSignals(True)
        self.mode_combo.setCurrentIndex(1 if enabled else 0)
        self.mode_combo.blockSignals(previous_state)

    def _on_mode_changed(self, index: int) -> None:
        self.theme_changed.emit(self.is_dark_mode)
