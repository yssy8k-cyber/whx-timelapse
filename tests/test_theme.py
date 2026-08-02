"""主题工具栏和样式测试。"""

from __future__ import annotations

import unittest

from PySide6.QtWidgets import QApplication, QMainWindow

from ui.style import apply_main_window_style
from ui.theme_toolbar import ThemeToolbar


class ThemeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QApplication.instance() or QApplication([])

    def test_toolbar_emits_theme_state(self) -> None:
        toolbar = ThemeToolbar()
        states: list[bool] = []
        toolbar.theme_changed.connect(states.append)

        toolbar.mode_combo.setCurrentIndex(1)

        self.assertTrue(toolbar.is_dark_mode)
        self.assertEqual(states, [True])
        toolbar.set_dark_mode(False)
        self.assertFalse(toolbar.is_dark_mode)

    def test_stylesheet_changes_between_light_and_dark(self) -> None:
        window = QMainWindow()
        apply_main_window_style(window, False)
        self.assertIn("#f5f7fa", window.styleSheet())

        apply_main_window_style(window, True)
        self.assertIn("#202124", window.styleSheet())


if __name__ == "__main__":
    unittest.main()
