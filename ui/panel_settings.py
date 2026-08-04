"""Dashboard 的截图、视频、文件、日志和设置页面。"""

from __future__ import annotations

from PySide6.QtCore import QDate, QTime, Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDateEdit,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPlainTextEdit,
    QProgressBar,
    QPushButton,
    QSpinBox,
    QTimeEdit,
    QVBoxLayout,
    QWidget,
)

from .icons import icon


class PanelSettingsMixin:
    """提供截图和视频相关设置页面，不读取或写入业务状态。"""

    def _build_capture_page(self) -> QWidget:
        page = self._scroll_page()
        top = QHBoxLayout()
        top.setSpacing(16)
        capture_card, capture_layout = self._card("截图计划", "按间隔抓取 JPEG")
        form = QFormLayout()
        form.setVerticalSpacing(14)
        self.interval_combo = QComboBox()
        self.interval_combo.addItems(["5 秒", "10 秒", "15 秒", "30 秒", "60 秒", "自定义"])
        self.custom_interval_spin = QSpinBox()
        self.custom_interval_spin.setRange(1, 86400)
        self.custom_interval_spin.setValue(60)
        self.custom_interval_spin.setSuffix(" 秒")
        self.interval_combo.setEnabled(False)
        self.custom_interval_spin.setEnabled(False)
        form.addRow("截图间隔", self.interval_combo)
        form.addRow("自定义间隔", self.custom_interval_spin)
        capture_layout.addLayout(form)
        actions = QHBoxLayout()
        self.start_button = QPushButton("开始截图")
        self.start_button.setIcon(icon("play", "#ffffff"))
        self.stop_button = QPushButton("停止")
        self.stop_button.setObjectName("secondaryButton")
        self.stop_button.setIcon(icon("stop"))
        self.start_button.setEnabled(False)
        self.stop_button.setEnabled(False)
        actions.addWidget(self.start_button)
        actions.addWidget(self.stop_button)
        actions.addStretch()
        capture_layout.addLayout(actions)
        top.addWidget(capture_card, 1)
        image_card, image_layout = self._card("图片保存", "JPEG 与保留策略")
        image_layout.addWidget(self._build_image_form())
        top.addWidget(image_card, 1)
        self._page_layout(page).addLayout(top)
        self._page_layout(page).addStretch()
        return page

    def _build_image_form(self) -> QWidget:
        form = QWidget()
        layout = QFormLayout(form)
        layout.setVerticalSpacing(14)
        directory_layout = QHBoxLayout()
        self.directory_edit = QLineEdit()
        self.browse_button = QPushButton("浏览")
        self.browse_button.setObjectName("secondaryButton")
        directory_layout.addWidget(self.directory_edit)
        directory_layout.addWidget(self.browse_button)
        self.quality_spin = QSpinBox()
        self.quality_spin.setRange(1, 100)
        self.quality_spin.setSuffix(" %")
        self.retention_combo = QComboBox()
        self.retention_combo.addItem("保留所有图片", "keep_all")
        self.retention_combo.addItem("视频生成成功后删除图片", "delete_after_video")
        self.retention_combo.addItem("只保留最近 N 天", "keep_recent_days")
        self.retention_days_spin = QSpinBox()
        self.retention_days_spin.setRange(1, 3650)
        self.retention_days_spin.setSuffix(" 天")
        layout.addRow("图片目录", directory_layout)
        layout.addRow("JPEG 质量", self.quality_spin)
        layout.addRow("保存策略", self.retention_combo)
        layout.addRow("保留天数", self.retention_days_spin)
        self.retention_combo.currentIndexChanged.connect(
            lambda: self.retention_days_spin.setEnabled(
                self.retention_combo.currentData() == "keep_recent_days"
            )
        )
        return form

    def _build_video_page(self) -> QWidget:
        page = self._scroll_page()
        settings_row = QHBoxLayout()
        settings_row.setSpacing(16)
        video_card, video_layout = self._card("视频输出", "MP4 / H.264")
        video_layout.addWidget(self._build_video_form())
        settings_row.addWidget(video_card, 1)
        schedule_card, schedule_layout = self._card("自动生成计划", "灵活安排输出")
        schedule_layout.addWidget(self._build_schedule_form())
        settings_row.addWidget(schedule_card, 1)
        self._page_layout(page).addLayout(settings_row)
        action_card, action_layout = self._card("视频任务", "按当前范围立即生成")
        self.generate_button = QPushButton("立即生成视频")
        self.generate_button.setIcon(icon("video", "#ffffff"))
        action_layout.addWidget(self.generate_button, 0, Qt.AlignLeft)
        progress_row = QHBoxLayout()
        self.video_progress = QProgressBar()
        self.video_progress.setRange(0, 100)
        self.video_progress.setValue(0)
        self.video_progress.setFormat("%p%")
        self.video_progress_label = QLabel("等待生成任务")
        progress_row.addWidget(self.video_progress, 1)
        progress_row.addWidget(self.video_progress_label)
        action_layout.addLayout(progress_row)
        self._page_layout(page).addWidget(action_card)
        self._page_layout(page).addStretch()
        return page

    def _build_video_form(self) -> QWidget:
        form = QWidget()
        layout = QFormLayout(form)
        layout.setVerticalSpacing(14)
        directory_layout = QHBoxLayout()
        self.video_directory_edit = QLineEdit()
        self.video_browse_button = QPushButton("浏览")
        self.video_browse_button.setObjectName("secondaryButton")
        self.open_video_directory_button = QPushButton("打开")
        self.open_video_directory_button.setObjectName("secondaryButton")
        directory_layout.addWidget(self.video_directory_edit)
        directory_layout.addWidget(self.video_browse_button)
        directory_layout.addWidget(self.open_video_directory_button)
        self.video_format_label = QLabel("MP4 (H.264)")
        self.fps_combo = QComboBox()
        self.fps_combo.addItems(["15 FPS", "24 FPS", "25 FPS", "30 FPS", "60 FPS"])
        self.filename_template_edit = QLineEdit()
        self.filename_template_edit.setPlaceholderText("Timelapse_{date}.mp4")
        self.overwrite_combo = QComboBox()
        self.overwrite_combo.addItem("自动重命名", "rename")
        self.overwrite_combo.addItem("自动覆盖", "overwrite")
        self.overwrite_combo.addItem("提示用户选择", "prompt")
        layout.addRow("视频目录", directory_layout)
        layout.addRow("输出格式", self.video_format_label)
        layout.addRow("视频帧率", self.fps_combo)
        layout.addRow("文件名模板", self.filename_template_edit)
        layout.addRow("同名文件", self.overwrite_combo)
        return form

    def _build_schedule_form(self) -> QWidget:
        form = QWidget()
        layout = QFormLayout(form)
        layout.setVerticalSpacing(12)
        self.schedule_mode_combo = QComboBox()
        self.schedule_mode_combo.addItem("手动生成", "manual")
        self.schedule_mode_combo.addItem("每隔固定时间", "interval")
        self.schedule_mode_combo.addItem("每天固定时间", "daily")
        self.schedule_interval_combo = QComboBox()
        for label, seconds in (("30 分钟", 1800), ("1 小时", 3600), ("3 小时", 10800),
                               ("6 小时", 21600), ("12 小时", 43200), ("24 小时", 86400)):
            self.schedule_interval_combo.addItem(label, seconds)
        self.schedule_interval_combo.addItem("自定义", "custom")
        self.schedule_custom_interval_spin = QSpinBox()
        self.schedule_custom_interval_spin.setRange(1, 3650)
        self.schedule_custom_interval_spin.setSuffix(" 分钟")
        self.schedule_time_edit = QTimeEdit(QTime(0, 0))
        self.schedule_time_edit.setDisplayFormat("HH:mm")
        self.range_combo = QComboBox()
        for label, value in (("今天", "today"), ("昨天", "yesterday"), ("最近 24 小时", "last_24_hours"),
                             ("最近 7 天", "last_7_days"), ("自定义日期范围", "custom")):
            self.range_combo.addItem(label, value)
        self.range_start_edit = QDateEdit(QDate.currentDate())
        self.range_end_edit = QDateEdit(QDate.currentDate())
        for editor in (self.range_start_edit, self.range_end_edit):
            editor.setCalendarPopup(True)
            editor.setDisplayFormat("yyyy-MM-dd")
        self.auto_open_output_check = QCheckBox("自动打开输出目录")
        self.completion_prompt_check = QCheckBox("弹出完成提示")
        self.log_generation_check = QCheckBox("写入视频生成日志")
        actions = QVBoxLayout()
        actions.setSpacing(8)
        for checkbox in (self.auto_open_output_check, self.completion_prompt_check, self.log_generation_check):
            actions.addWidget(checkbox)
        layout.addRow("计划模式", self.schedule_mode_combo)
        layout.addRow("生成间隔", self.schedule_interval_combo)
        layout.addRow("自定义间隔", self.schedule_custom_interval_spin)
        layout.addRow("每天时间", self.schedule_time_edit)
        layout.addRow("生成范围", self.range_combo)
        layout.addRow("开始日期", self.range_start_edit)
        layout.addRow("结束日期", self.range_end_edit)
        layout.addRow("完成动作", actions)
        return form

    def _build_files_page(self) -> QWidget:
        page = self._scroll_page()
        image_card, image_layout = self._card("图片目录", "采集文件位置")
        image_layout.addWidget(QLabel("图片保存目录、JPEG 质量和保留策略可在“截图计划”页面调整。"))
        image_button = QPushButton("前往截图计划")
        image_button.setObjectName("secondaryButton")
        image_button.clicked.connect(lambda: self._switch_page(2))
        image_layout.addWidget(image_button, 0, Qt.AlignLeft)
        self._page_layout(page).addWidget(image_card)
        video_card, video_layout = self._card("视频目录", "生成文件位置")
        video_layout.addWidget(QLabel("视频输出目录、文件名模板和同名文件策略可在“视频生成”页面调整。"))
        video_button = QPushButton("前往视频生成")
        video_button.setObjectName("secondaryButton")
        video_button.clicked.connect(lambda: self._switch_page(3))
        video_layout.addWidget(video_button, 0, Qt.AlignLeft)
        self._page_layout(page).addWidget(video_card)
        self._page_layout(page).addStretch()
        return page

    def _build_logs_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        card, card_layout = self._card("系统日志", "连接、截图、视频与异常")
        self.log_view = QPlainTextEdit()
        self.log_view.setObjectName("logView")
        self.log_view.setReadOnly(True)
        self.log_view.setPlaceholderText("暂无日志")
        card_layout.addWidget(self.log_view, 1)
        layout.addWidget(card, 1)
        return page

    def _build_settings_page(self) -> QWidget:
        page = self._scroll_page()
        theme_card, theme_layout = self._card("外观主题", "浅色、深色或跟随系统")
        theme_layout.addWidget(QLabel("可使用窗口顶部的主题选择器切换界面外观。"))
        self._page_layout(page).addWidget(theme_card)
        runtime_card, runtime_layout = self._card("运行状态", "长期运行建议")
        runtime_layout.addWidget(QLabel("RTSP 预览、截图和视频生成使用独立线程，关闭窗口时会自动释放资源。"))
        self._page_layout(page).addWidget(runtime_card)
        self._page_layout(page).addStretch()
        return page
