"""Timelapse Studio 统一界面样式。"""

from __future__ import annotations

from PySide6.QtWidgets import QMainWindow


def apply_main_window_style(window: QMainWindow, dark_mode: bool = False) -> None:
    """应用浅色或深色 Windows 风格基础样式。"""
    colors = {
        "window": "#202124" if dark_mode else "#f5f7fa",
        "panel": "#2b2d30" if dark_mode else "#ffffff",
        "text": "#f3f4f6" if dark_mode else "#1f2937",
        "heading": "#ffffff" if dark_mode else "#111827",
        "muted": "#aeb4bf" if dark_mode else "#6b7280",
        "border": "#454a52" if dark_mode else "#e2e8f0",
        "input_border": "#5a616d" if dark_mode else "#d1d5db",
        "selected": "#315b91" if dark_mode else "#dbeafe",
        "selected_text": "#ffffff" if dark_mode else "#1d4ed8",
        "status_text": "#c5cad3" if dark_mode else "#4b5563",
    }
    window.setStyleSheet(
        f"""
        QWidget {{ font-family: 'Microsoft YaHei', 'Segoe UI', sans-serif; font-size: 13px; }}
        QMainWindow, QWidget {{ background: {colors['window']}; color: {colors['text']}; }}
        #titleLabel {{ font-size: 25px; font-weight: 700; color: {colors['heading']}; }}
        #subtitleLabel {{ color: {colors['muted']}; margin-bottom: 3px; }}
        #sectionLabel {{ font-size: 15px; font-weight: 700; color: {colors['text']}; }}
        QToolBar {{ background: {colors['panel']}; border-bottom: 1px solid {colors['border']}; spacing: 8px; padding: 5px 12px; }}
        QGroupBox {{ background: {colors['panel']}; border: 1px solid {colors['border']}; border-radius: 6px; margin-top: 8px; padding: 12px; }}
        QGroupBox::title {{ subcontrol-origin: margin; left: 12px; padding: 0 5px; color: {colors['text']}; font-weight: 600; }}
        QListWidget, QLineEdit, QPlainTextEdit, QComboBox, QSpinBox {{ background: {colors['panel']}; color: {colors['text']}; border: 1px solid {colors['input_border']}; border-radius: 4px; padding: 7px; }}
        QListWidget::item {{ padding: 9px 7px; border-radius: 4px; }}
        QListWidget::item:selected {{ background: {colors['selected']}; color: {colors['selected_text']}; }}
        QPushButton {{ background: #2563eb; color: #ffffff; border: none; border-radius: 4px; padding: 8px 15px; font-weight: 600; }}
        QPushButton:hover {{ background: #1d4ed8; }}
        QPushButton:disabled {{ background: #64748b; color: #d1d5db; }}
        QStatusBar {{ background: {colors['panel']}; border-top: 1px solid {colors['border']}; color: {colors['status_text']}; }}
        """
    )
