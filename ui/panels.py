"""Timelapse Studio 的主窗口布局入口。"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QHBoxLayout, QLabel, QMainWindow, QStackedWidget, QStatusBar, QVBoxLayout, QWidget

from .panel_common import PanelCommonMixin
from .panel_settings import PanelSettingsMixin


class PanelMixin(PanelCommonMixin, PanelSettingsMixin):
    """组合 Dashboard 页面，并保留旧布局方法名。"""

    def _build_ui(self) -> None:
        """创建主窗口骨架和页面导航。"""
        self.setStatusBar(QStatusBar(self))
        self.statusBar().showMessage("就绪")
        central = QWidget(self)
        central.setObjectName("centralArea")
        root = QHBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        root.addWidget(self._build_sidebar())
        content = QWidget(central)
        content.setObjectName("contentArea")
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(32, 24, 32, 22)
        content_layout.setSpacing(18)
        header = QHBoxLayout()
        title_box = QVBoxLayout()
        title_box.setSpacing(2)
        self.page_title = QLabel("首页")
        self.page_title.setObjectName("pageTitle")
        self.page_subtitle = QLabel("WHX自动化工具 · 长期延时摄影工作台")
        self.page_subtitle.setObjectName("pageSubtitle")
        title_box.addWidget(self.page_title)
        title_box.addWidget(self.page_subtitle)
        header.addLayout(title_box)
        header.addStretch()
        self.header_status = QLabel("● 系统就绪")
        self.header_status.setObjectName("statusBadge")
        header.addWidget(self.header_status, 0, Qt.AlignVCenter)
        content_layout.addLayout(header)
        self.pages = QStackedWidget(content)
        self.pages.setObjectName("pageStack")
        for page in (self._build_home_page(), self._build_camera_page(), self._build_capture_page(),
                     self._build_video_page(), self._build_files_page(), self._build_logs_page(),
                     self._build_settings_page()):
            self.pages.addWidget(page)
        content_layout.addWidget(self.pages, 1)
        root.addWidget(content, 1)
        self.setCentralWidget(central)

    def _build_workspace_panel(self) -> QWidget:
        """兼容旧调用方；新布局由页面栈承载。"""
        return self.pages

    def _build_device_panel(self) -> QWidget:
        """兼容旧调用方；设备列表现在位于摄像头页面。"""
        return self.pages.widget(1)

    def _on_capture_succeeded(self, image_path: str) -> None:
        self.statusBar().showMessage(f"最近截图: {image_path}")
        self._set_dashboard_capture_state("运行中 · 最近成功")

    def _on_capture_failed(self, message: str) -> None:
        self.statusBar().showMessage(f"截图失败: {message}")
        self._set_dashboard_capture_state("运行中 · 有失败")


__all__ = ["PanelMixin"]
