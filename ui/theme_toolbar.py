"""顶部主题切换工具栏。"""

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QComboBox, QLabel, QToolBar


class ThemeToolbar(QToolBar):
    """提供浅色和深色主题选择。"""

    theme_changed = Signal(bool)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("themeToolbar")
        self.setMovable(False)
        self.setFloatable(False)
        self.addWidget(QLabel("主题"))
        self.mode_combo = QComboBox()
        self.mode_combo.addItems(["浅色", "深色"])
        self.mode_combo.currentIndexChanged.connect(self._on_mode_changed)
        self.addWidget(self.mode_combo)

    @property
    def is_dark_mode(self) -> bool:
        """返回当前是否为深色主题。"""
        return self.mode_combo.currentIndex() == 1

    def set_dark_mode(self, enabled: bool) -> None:
        """恢复主题配置而不重复发出切换信号。"""
        previous_state = self.mode_combo.blockSignals(True)
        self.mode_combo.setCurrentIndex(1 if enabled else 0)
        self.mode_combo.blockSignals(previous_state)

    def _on_mode_changed(self, index: int) -> None:
        self.theme_changed.emit(index == 1)
