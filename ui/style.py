"""Timelapse Studio 的 Fluent 风格主题样式。"""

from __future__ import annotations

from PySide6.QtWidgets import QMainWindow


def apply_main_window_style(window: QMainWindow, dark_mode: bool = False) -> None:
    """应用浅色或深色 Dashboard 主题。"""
    colors = {
        "window": "#202124" if dark_mode else "#f5f7fa",
        "sidebar": "#181a1f" if dark_mode else "#ffffff",
        "card": "#2b2d30" if dark_mode else "#ffffff",
        "input": "#24262a" if dark_mode else "#f8fafc",
        "text": "#f3f4f6" if dark_mode else "#172033",
        "heading": "#ffffff" if dark_mode else "#0f172a",
        "muted": "#aeb4bf" if dark_mode else "#64748b",
        "border": "#454a52" if dark_mode else "#e5eaf1",
        "input_border": "#555d68" if dark_mode else "#d8e0ea",
        "selected": "#263f67" if dark_mode else "#eaf2ff",
        "selected_text": "#93c5fd" if dark_mode else "#1d4ed8",
        "hover": "#30343b" if dark_mode else "#f3f6fa",
        "status": "#334155" if dark_mode else "#eff6ff",
    }
    window.setStyleSheet(
        f"""
        QWidget {{
            font-family: 'Segoe UI', 'Microsoft YaHei', sans-serif;
            font-size: 13px;
            color: {colors['text']};
        }}
        QMainWindow, #centralArea, #contentArea {{ background: {colors['window']}; }}
        #sidebar {{
            background: {colors['sidebar']};
            border-right: 1px solid {colors['border']};
        }}
        #brandMark {{
            background: #2563eb;
            color: #ffffff;
            border-radius: 10px;
            font-size: 15px;
            font-weight: 700;
            min-width: 36px;
            min-height: 36px;
            qproperty-alignment: AlignCenter;
        }}
        #brandName {{ color: {colors['heading']}; font-size: 16px; font-weight: 700; }}
        #brandVersion, #sidebarFooter {{ color: {colors['muted']}; font-size: 10px; letter-spacing: 1px; }}
        #pageTitle {{ color: {colors['heading']}; font-size: 22px; font-weight: 700; }}
        #pageSubtitle, #cardDescription, .mutedLabel {{ color: {colors['muted']}; font-size: 12px; }}
        #statusBadge {{
            background: {colors['status']};
            color: #2563eb;
            border-radius: 14px;
            padding: 7px 12px;
            font-weight: 600;
        }}
        #sidebarSummary {{
            background: {colors['input']};
            border: 1px solid {colors['border']};
            border-radius: 10px;
        }}
        #sidebarDevice {{ color: {colors['heading']}; font-weight: 600; }}
        #sidebarConnection {{ color: {colors['muted']}; font-size: 12px; }}
        QPushButton#navButton {{
            background: transparent;
            color: {colors['muted']};
            border: none;
            border-radius: 10px;
            text-align: left;
            padding: 0 12px;
            font-weight: 600;
        }}
        QPushButton#navButton:hover {{ background: {colors['hover']}; color: {colors['heading']}; }}
        QPushButton#navButton:checked {{ background: {colors['selected']}; color: {colors['selected_text']}; }}
        QFrame#card, QFrame#previewCard {{
            background: {colors['card']};
            border: 1px solid {colors['border']};
            border-radius: 12px;
        }}
        QFrame#metricCard {{
            background: {colors['card']};
            border: 1px solid {colors['border']};
            border-radius: 10px;
        }}
        QProgressBar {{
            background: {colors['input']};
            border: 1px solid {colors['border']};
            border-radius: 5px;
            min-height: 10px;
            text-align: center;
        }}
        QProgressBar::chunk {{ background: #f59e0b; border-radius: 4px; }}
        #cardTitle {{ color: {colors['heading']}; font-size: 16px; font-weight: 700; }}
        #metricTitle {{ color: {colors['muted']}; font-size: 12px; }}
        #metricValue, #cameraMetric, #captureMetric, #videoMetric, #storageMetric {{
            color: {colors['heading']}; font-size: 18px; font-weight: 700;
        }}
        #pageScroll {{ background: transparent; border: none; }}
        QScrollArea > QWidget > QWidget {{ background: transparent; }}
        QFrame#previewFrame {{ background: #09111f; border: 1px solid #1e293b; border-radius: 9px; }}
        QLabel#previewStatusLabel {{ color: {colors['muted']}; font-size: 12px; }}
        QLabel#previewOverlayLabel {{
            background: rgba(2, 6, 23, 190);
            color: #f8fafc;
            border-radius: 6px;
            padding: 5px 8px;
            font-size: 11px;
        }}
        QLabel#recordingLabel {{
            background: #16a34a;
            color: #ffffff;
            border-radius: 6px;
            padding: 5px 9px;
            font-weight: 700;
        }}
        QListWidget, QLineEdit, QPlainTextEdit, QComboBox, QSpinBox, QDateEdit, QTimeEdit {{
            background: {colors['input']};
            color: {colors['text']};
            border: 1px solid {colors['input_border']};
            border-radius: 8px;
            padding: 8px 10px;
            selection-background-color: #2563eb;
        }}
        QLineEdit:focus, QComboBox:focus, QSpinBox:focus, QDateEdit:focus, QTimeEdit:focus {{
            border: 1px solid #2563eb;
        }}
        QListWidget {{ padding: 5px; }}
        QListWidget::item {{ padding: 11px 8px; border-radius: 7px; }}
        QListWidget::item:hover {{ background: {colors['hover']}; }}
        QListWidget::item:selected {{ background: {colors['selected']}; color: {colors['selected_text']}; }}
        QPlainTextEdit#logView, QPlainTextEdit#homeLogView {{
            background: {colors['input']};
            border: 1px solid {colors['border']};
            font-family: 'Cascadia Mono', 'Consolas', monospace;
            font-size: 12px;
        }}
        QPushButton {{
            background: #2563eb;
            color: #ffffff;
            border: none;
            border-radius: 8px;
            min-height: 36px;
            padding: 0 15px;
            font-weight: 600;
        }}
        QPushButton:hover {{ background: #1d4ed8; }}
        QPushButton:pressed {{ background: #1e40af; }}
        QPushButton:disabled {{ background: #94a3b8; color: #e2e8f0; }}
        QPushButton#secondaryButton {{ background: {colors['hover']}; color: {colors['text']}; border: 1px solid {colors['input_border']}; }}
        QPushButton#secondaryButton:hover {{ background: {colors['selected']}; color: {colors['selected_text']}; }}
        QCheckBox {{ spacing: 8px; }}
        QCheckBox::indicator {{ width: 17px; height: 17px; border-radius: 5px; border: 1px solid {colors['input_border']}; background: {colors['input']}; }}
        QCheckBox::indicator:checked {{ background: #2563eb; border-color: #2563eb; }}
        QStatusBar {{ background: {colors['card']}; border-top: 1px solid {colors['border']}; color: {colors['muted']}; }}
        QToolBar#themeToolbar {{ background: transparent; border: none; padding: 6px 20px; spacing: 8px; }}
        """
    )


__all__ = ["apply_main_window_style"]
