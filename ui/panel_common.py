"""Dashboard 的导航、首页和摄像头页面。"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QFormLayout,
    QFrame,
    QGraphicsDropShadowEffect,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QPushButton,
    QPlainTextEdit,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from .icons import icon
from .preview_panel import PreviewPanel


class PanelCommonMixin:
    """提供导航、首页和摄像头配置页的布局方法。"""

    _nav_items = (("首页", "home"), ("摄像头", "camera"), ("截图计划", "capture"),
                  ("视频生成", "video"), ("文件管理", "folder"), ("日志", "log"),
                  ("设置", "settings"))

    def _build_sidebar(self) -> QWidget:
        """创建固定导航栏和设备摘要。"""
        sidebar = QFrame()
        sidebar.setObjectName("sidebar")
        sidebar.setMinimumWidth(208)
        sidebar.setMaximumWidth(248)
        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(18, 22, 14, 18)
        layout.setSpacing(8)
        brand = QHBoxLayout()
        brand.setSpacing(10)
        mark = QLabel("TS")
        mark.setObjectName("brandMark")
        brand_text = QVBoxLayout()
        brand_text.setSpacing(0)
        name = QLabel("海康威视延时摄影")
        name.setObjectName("brandName")
        version = QLabel("STUDIO  /  1.0")
        version.setObjectName("brandVersion")
        brand_text.addWidget(name)
        brand_text.addWidget(version)
        brand.addWidget(mark)
        brand.addLayout(brand_text)
        layout.addLayout(brand)
        layout.addSpacing(24)
        self.nav_buttons: list[QPushButton] = []
        for index, (label, icon_name) in enumerate(self._nav_items):
            button = QPushButton(label)
            button.setObjectName("navButton")
            button.setCheckable(True)
            button.setIcon(icon(icon_name, "#64748b", 19))
            button.setMinimumHeight(42)
            button.clicked.connect(lambda _checked=False, i=index: self._switch_page(i))
            self.nav_buttons.append(button)
            layout.addWidget(button)
        self.nav_buttons[0].setChecked(True)
        layout.addStretch()
        summary = QFrame()
        summary.setObjectName("sidebarSummary")
        summary_layout = QVBoxLayout(summary)
        summary_layout.setContentsMargins(14, 13, 14, 13)
        summary_layout.setSpacing(5)
        summary_layout.addWidget(QLabel("当前设备"))
        self.sidebar_device_label = QLabel("海康威视摄像头 1")
        self.sidebar_device_label.setObjectName("sidebarDevice")
        self.sidebar_connection_label = QLabel("● 未连接")
        self.sidebar_connection_label.setObjectName("sidebarConnection")
        summary_layout.addWidget(self.sidebar_device_label)
        summary_layout.addWidget(self.sidebar_connection_label)
        layout.addWidget(summary)
        footer = QLabel("长期运行 · 稳定采集")
        footer.setObjectName("sidebarFooter")
        layout.addWidget(footer)
        return sidebar

    def _switch_page(self, index: int) -> None:
        """切换页面并同步导航按钮状态。"""
        if index < 0 or index >= self.pages.count():
            return
        self.pages.setCurrentIndex(index)
        for row, button in enumerate(self.nav_buttons):
            button.setChecked(row == index)
        self.page_title.setText(self._nav_items[index][0])
        subtitles = ("运行概览与采集状态", "管理 RTSP 设备连接与实时预览",
                     "设置定时截图与图片保存策略", "配置视频参数与自动生成计划",
                     "查看图片和视频输出位置", "查看系统运行记录", "调整应用外观与运行偏好")
        self.page_subtitle.setText(subtitles[index])

    @staticmethod
    def _card(title: str, description: str = "") -> tuple[QFrame, QVBoxLayout]:
        """创建统一卡片和标题栏。"""
        card = QFrame()
        card.setObjectName("card")
        shadow = QGraphicsDropShadowEffect(card)
        shadow.setBlurRadius(18)
        shadow.setOffset(0, 3)
        shadow.setColor(QColor(15, 23, 42, 28))
        card.setGraphicsEffect(shadow)
        layout = QVBoxLayout(card)
        layout.setContentsMargins(20, 18, 20, 20)
        layout.setSpacing(14)
        heading = QHBoxLayout()
        title_label = QLabel(title)
        title_label.setObjectName("cardTitle")
        heading.addWidget(title_label)
        heading.addStretch()
        if description:
            desc = QLabel(description)
            desc.setObjectName("cardDescription")
            heading.addWidget(desc)
        layout.addLayout(heading)
        return card, layout

    @staticmethod
    def _metric_card(title: str, value: str, object_name: str = "") -> QFrame:
        """创建首页状态指标卡。"""
        card = QFrame()
        card.setObjectName("metricCard")
        shadow = QGraphicsDropShadowEffect(card)
        shadow.setBlurRadius(16)
        shadow.setOffset(0, 2)
        shadow.setColor(QColor(15, 23, 42, 22))
        card.setGraphicsEffect(shadow)
        layout = QVBoxLayout(card)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(4)
        label = QLabel(title)
        label.setObjectName("metricTitle")
        value_label = QLabel(value)
        value_label.setObjectName(object_name or "metricValue")
        layout.addWidget(label)
        layout.addWidget(value_label)
        card.value_label = value_label  # type: ignore[attr-defined]
        return card

    def _build_home_page(self) -> QWidget:
        page = self._scroll_page()
        body = QHBoxLayout()
        body.setSpacing(16)
        self.preview_panel = PreviewPanel(page)
        self.preview_panel.setMinimumWidth(500)
        body.addWidget(self.preview_panel, 2)
        status_column = QVBoxLayout()
        status_column.setSpacing(12)
        self.camera_metric = self._metric_card("摄像头状态", "未连接", "cameraMetric")
        self.capture_metric = self._metric_card("截图任务", "未运行", "captureMetric")
        self.video_metric = self._metric_card("视频生成", "待命", "videoMetric")
        self.storage_metric = self._metric_card("存储空间", "等待检测", "storageMetric")
        for card in (self.camera_metric, self.capture_metric, self.video_metric, self.storage_metric):
            status_column.addWidget(card)
        status_column.addStretch()
        body.addLayout(status_column, 1)
        self._page_layout(page).addLayout(body)
        log_card, log_layout = self._card("最近日志", "实时更新")
        self.home_log_view = QPlainTextEdit()
        self.home_log_view.setObjectName("homeLogView")
        self.home_log_view.setReadOnly(True)
        self.home_log_view.setMaximumBlockCount(6)
        self.home_log_view.setFixedHeight(126)
        self.home_log_view.setPlaceholderText("连接状态和运行日志会显示在这里")
        log_layout.addWidget(self.home_log_view)
        self._page_layout(page).addWidget(log_card)
        return page

    def _build_camera_page(self) -> QWidget:
        page = self._scroll_page()
        row = QHBoxLayout()
        row.setSpacing(16)
        device_card, device_layout = self._card("设备列表", "已保存的摄像头")
        self.device_list = QListWidget()
        self.device_list.setObjectName("deviceList")
        self.device_list.addItem("海康威视摄像头 1")
        self.device_list.setCurrentRow(0)
        device_layout.addWidget(self.device_list, 1)
        device_buttons = QHBoxLayout()
        self.add_device_button = QPushButton("添加设备")
        self.add_device_button.setIcon(icon("plus"))
        self.remove_device_button = QPushButton("删除")
        self.remove_device_button.setObjectName("secondaryButton")
        self.remove_device_button.setEnabled(False)
        device_buttons.addWidget(self.add_device_button)
        device_buttons.addWidget(self.remove_device_button)
        device_layout.addLayout(device_buttons)
        row.addWidget(device_card, 1)
        connection_card, connection_layout = self._card("连接设置", "RTSP 视频流")
        connection_layout.addWidget(self._build_connection_form())
        connection_card.setMinimumWidth(500)
        row.addWidget(connection_card, 2)
        self._page_layout(page).addLayout(row)
        hint_card, hint_layout = self._card("实时预览", "预览画面位于首页")
        hint_layout.addWidget(QLabel("连接成功后，首页会自动显示实时画面。刷新预览不会影响截图任务。"))
        self._page_layout(page).addWidget(hint_card)
        self._page_layout(page).addStretch()
        return page

    def _build_connection_form(self) -> QWidget:
        form = QWidget()
        layout = QFormLayout(form)
        layout.setLabelAlignment(Qt.AlignLeft)
        layout.setFormAlignment(Qt.AlignTop)
        layout.setHorizontalSpacing(18)
        layout.setVerticalSpacing(14)
        self.rtsp_edit = QLineEdit()
        self.rtsp_edit.setPlaceholderText("rtsp://192.168.1.64:554/Streaming/Channels/101")
        self.username_edit = QLineEdit()
        self.password_edit = QLineEdit()
        self.password_edit.setEchoMode(QLineEdit.Password)
        self.connect_button = QPushButton("连接摄像头")
        self.connect_button.setIcon(icon("camera", "#ffffff"))
        self.disconnect_button = QPushButton("断开连接")
        self.disconnect_button.setObjectName("secondaryButton")
        self.disconnect_button.setEnabled(False)
        actions = QHBoxLayout()
        actions.addWidget(self.connect_button)
        actions.addWidget(self.disconnect_button)
        actions.addStretch()
        layout.addRow("RTSP 地址", self.rtsp_edit)
        layout.addRow("用户名", self.username_edit)
        layout.addRow("密码", self.password_edit)
        layout.addRow("操作", actions)
        return form

    @staticmethod
    def _scroll_page() -> QWidget:
        """创建可滚动页面，适配小窗口。"""
        scroll = QScrollArea()
        scroll.setObjectName("pageScroll")
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(2, 2, 8, 12)
        content_layout.setSpacing(16)
        scroll.setWidget(content)
        return scroll

    @staticmethod
    def _page_layout(page: QWidget) -> QVBoxLayout:
        """取得滚动页面内部布局。"""
        content = page.widget()  # type: ignore[attr-defined]
        return content.layout()  # type: ignore[return-value]
