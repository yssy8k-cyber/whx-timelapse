"""保存设置、视频计划和生成任务的主窗口协作层。"""

from __future__ import annotations

from datetime import date, datetime
from pathlib import Path

from PySide6.QtCore import QDate, QTime, QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import QFileDialog, QMessageBox, QDateEdit

from video.generation_plan import (
    image_directories,
    render_filename,
    resolve_date_range,
)


class VideoPlanIntegrationMixin:
    """管理保存目录、视频输出和自动生成计划。"""

    def _load_video_config_into_ui(self) -> None:
        """将配置中的保存、视频和计划字段恢复到控件。"""
        self.directory_edit.setText(self.config.save_directory)
        self.quality_spin.setValue(self.config.jpeg_quality)
        self.retention_days_spin.setValue(self.config.image_retention_days)
        self.retention_combo.setCurrentIndex(
            max(0, self.retention_combo.findData(self.config.image_retention_policy))
        )
        self.video_directory_edit.setText(self.config.video_output_directory)
        self.fps_combo.setCurrentText(f"{self.config.video_fps} FPS")
        self.filename_template_edit.setText(self.config.video_filename_template)
        self.overwrite_combo.setCurrentIndex(
            max(0, self.overwrite_combo.findData(self.config.video_overwrite_policy))
        )
        self.schedule_mode_combo.setCurrentIndex(
            max(0, self.schedule_mode_combo.findData(self.config.schedule_mode))
        )
        self._set_schedule_interval(self.config.schedule_interval_seconds)
        parsed_time = QTime.fromString(self.config.schedule_daily_time, "HH:mm")
        if parsed_time.isValid():
            self.schedule_time_edit.setTime(parsed_time)
        self.range_combo.setCurrentIndex(
            max(0, self.range_combo.findData(self.config.generation_range))
        )
        self._set_date_edit(self.range_start_edit, self.config.custom_range_start)
        self._set_date_edit(self.range_end_edit, self.config.custom_range_end)
        self.auto_open_output_check.setChecked(self.config.auto_open_output_directory)
        self.completion_prompt_check.setChecked(self.config.show_completion_prompt)
        self.log_generation_check.setChecked(self.config.log_video_generation)
        self._update_plan_controls()

    def _read_video_config_fields(self) -> dict[str, object]:
        """读取保存、视频和计划控件，供主窗口保存 JSON。"""
        schedule_mode = str(self.schedule_mode_combo.currentData())
        retention_policy = str(self.retention_combo.currentData())
        return {
            "save_directory": self.directory_edit.text().strip(),
            "video_output_directory": self.video_directory_edit.text().strip(),
            "jpeg_quality": self.quality_spin.value(),
            "video_fps": int(self.fps_combo.currentText().split()[0]),
            "image_retention_policy": retention_policy,
            "image_retention_days": self.retention_days_spin.value(),
            "delete_images_after_video": retention_policy == "delete_after_video",
            "video_filename_template": self.filename_template_edit.text().strip(),
            "video_overwrite_policy": str(self.overwrite_combo.currentData()),
            "schedule_mode": schedule_mode,
            "schedule_interval_seconds": self._selected_schedule_interval(),
            "schedule_daily_time": self.schedule_time_edit.time().toString("HH:mm"),
            "generation_range": str(self.range_combo.currentData()),
            "custom_range_start": self.range_start_edit.date().toString("yyyy-MM-dd"),
            "custom_range_end": self.range_end_edit.date().toString("yyyy-MM-dd"),
            "auto_open_output_directory": self.auto_open_output_check.isChecked(),
            "show_completion_prompt": self.completion_prompt_check.isChecked(),
            "log_video_generation": self.log_generation_check.isChecked(),
            "auto_generate_video": schedule_mode != "manual",
        }

    def _start_generation_schedule(self) -> None:
        """按当前计划启动或停止自动生成线程。"""
        mode = str(self.schedule_mode_combo.currentData())
        if mode == "manual":
            self.auto_video_controller.stop()
            return
        try:
            self.auto_video_controller.stop()
            self.auto_video_controller.start(
                mode,
                self._selected_schedule_interval(),
                self.schedule_time_edit.time().toString("HH:mm"),
            )
            self.statusBar().showMessage("视频生成计划已启用")
        except ValueError as error:
            self.logger.error("启动视频生成计划失败: %s", error)
            self.statusBar().showMessage(str(error))

    def _on_schedule_changed(self) -> None:
        """计划模式变化后立即保存并重新启动调度器。"""
        self._update_plan_controls()
        self._save_config()
        self._start_generation_schedule()

    def _update_plan_controls(self) -> None:
        mode = str(self.schedule_mode_combo.currentData())
        self.schedule_interval_combo.setEnabled(mode == "interval")
        self.schedule_custom_interval_spin.setEnabled(
            mode == "interval" and self.schedule_interval_combo.currentData() == "custom"
        )
        self.schedule_time_edit.setEnabled(mode == "daily")
        custom_range = self.range_combo.currentData() == "custom"
        self.range_start_edit.setEnabled(custom_range)
        self.range_end_edit.setEnabled(custom_range)

    def _on_schedule_interval_changed(self) -> None:
        self._update_plan_controls()
        self._save_config()

    def _on_range_changed(self) -> None:
        self._update_plan_controls()
        self._save_config()

    def _selected_schedule_interval(self) -> int:
        value = self.schedule_interval_combo.currentData()
        if value == "custom":
            return self.schedule_custom_interval_spin.value() * 60
        return int(value)

    def _set_schedule_interval(self, seconds: int) -> None:
        index = self.schedule_interval_combo.findData(seconds)
        if index >= 0:
            self.schedule_interval_combo.setCurrentIndex(index)
            return
        self.schedule_interval_combo.setCurrentIndex(
            self.schedule_interval_combo.findData("custom")
        )
        self.schedule_custom_interval_spin.setValue(max(1, round(seconds / 60)))

    def _set_date_edit(self, editor: QDateEdit, value: str) -> None:
        parsed = QDate.fromString(value, "yyyy-MM-dd") if value else QDate.currentDate()
        editor.setDate(parsed if parsed.isValid() else QDate.currentDate())

    def _generate_video(self) -> None:
        """手动点击按钮生成当前计划范围的视频。"""
        self._start_video_generation(automatic=False)

    def _start_auto_video(self, _trigger_date: str) -> None:
        """自动计划触发时按当前范围配置生成视频。"""
        self._start_video_generation(automatic=True)

    def _start_video_generation(self, automatic: bool) -> None:
        try:
            range_value = str(self.range_combo.currentData())
            date_range = resolve_date_range(
                range_value,
                now=datetime.now(),
                custom_start=self._widget_date(self.range_start_edit),
                custom_end=self._widget_date(self.range_end_edit),
            )
            image_root_text = self.directory_edit.text().strip()
            video_root_text = self.video_directory_edit.text().strip()
            if not image_root_text or not video_root_text:
                raise ValueError("图片目录和视频输出目录都不能为空")
            root = Path(image_root_text)
            directories = image_directories(root, date_range)
            camera_name = self.config.devices[self._active_device_index].name
            filename = render_filename(
                self.filename_template_edit.text().strip(),
                camera_name,
                date_range,
            )
            target = Path(video_root_text) / filename
            overwrite_policy = self._resolve_conflict_policy(target, automatic)
            if overwrite_policy is None:
                return
        except (OSError, ValueError) as error:
            self.logger.error("准备视频生成任务失败: %s", error)
            QMessageBox.warning(self, "无法生成视频", str(error))
            return

        retention_policy = str(self.retention_combo.currentData())
        started = self.video_controller.start(
            directories,
            int(self.fps_combo.currentText().split()[0]),
            retention_policy == "delete_after_video",
            output_path=target,
            retention_policy=retention_policy,
            retention_days=self.retention_days_spin.value(),
            image_root_directory=root,
            overwrite_policy=overwrite_policy,
            image_start_datetime=date_range.start_datetime,
            image_end_datetime=date_range.end_datetime,
            log_generation=self.log_generation_check.isChecked(),
        )
        if started:
            self._auto_video_active = automatic
            self._active_video_task_id = None
            self.video_progress.setValue(0)
            self.video_progress_label.setText("准备任务...")
            if getattr(self, "database", None) is not None:
                try:
                    image_count = sum(
                        1
                        for directory in directories
                        if directory.exists()
                        for image_path in directory.iterdir()
                        if image_path.is_file() and image_path.suffix.lower() == ".jpg"
                    )
                    self._active_video_task_id = self.database.create_video_task(
                        camera_name,
                        directories[0],
                        target,
                        image_count,
                    )
                except Exception as error:
                    self.logger.warning("写入视频任务记录失败: %s", error)
            self.generate_button.setEnabled(False)
            message = "正在自动生成视频..." if automatic else "正在生成视频..."
            self.statusBar().showMessage(message)
        else:
            self.logger.warning("视频生成任务正在运行，忽略新的生成请求")

    def _resolve_conflict_policy(self, target: Path, automatic: bool) -> str | None:
        policy = str(self.overwrite_combo.currentData())
        if policy != "prompt" or not target.exists():
            return policy
        if automatic:
            self.logger.warning("自动计划遇到同名视频，将自动重命名: %s", target)
            return "rename"
        answer = QMessageBox.question(
            self,
            "视频已存在",
            f"文件已存在：\n{target}\n\n是否覆盖？选择“否”将自动重命名。",
            QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel,
            QMessageBox.No,
        )
        if answer == QMessageBox.Cancel:
            return None
        return "overwrite" if answer == QMessageBox.Yes else "rename"

    def _on_video_generated(self, output_path: str) -> None:
        self._auto_video_active = False
        self._finish_video_task("completed")
        self.video_progress.setValue(100)
        self.video_progress_label.setText("已完成")
        self.generate_button.setEnabled(True)
        if self.log_generation_check.isChecked():
            self.logger.info("视频生成成功：%s", output_path)
        self.statusBar().showMessage(f"视频生成成功: {output_path}")
        if self.auto_open_output_check.isChecked():
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(Path(output_path).parent)))
        if self.completion_prompt_check.isChecked():
            QMessageBox.information(
                self,
                "视频生成完成",
                f"视频已保存到：\n{output_path}",
            )

    def _on_video_failed(self, message: str) -> None:
        automatic = self._auto_video_active
        self._auto_video_active = False
        self._finish_video_task("failed", message)
        self.video_progress_label.setText("生成失败")
        self.generate_button.setEnabled(True)
        self.statusBar().showMessage("视频生成失败")
        self.logger.error("视频生成失败: %s", message)
        if not automatic:
            QMessageBox.warning(self, "视频生成失败", message)

    def _on_video_progress(self, completed: int, total: int, message: str) -> None:
        """将后台图片准备和 FFmpeg 阶段映射为用户可读进度。"""
        if message == "视频生成完成":
            percent = 100
        elif message == "正在调用 FFmpeg":
            percent = 90
        else:
            percent = round(completed * 80 / total) if total else 0
        self.video_progress.setValue(percent)
        self.video_progress_label.setText(f"{message} {completed:,}/{total:,}")
        self.statusBar().showMessage(f"{message}：{completed:,}/{total:,}")

    def _finish_video_task(self, status: str, error_message: str = "") -> None:
        task_id = getattr(self, "_active_video_task_id", None)
        database = getattr(self, "database", None)
        if task_id is None or database is None:
            return
        try:
            database.finish_video_task(task_id, status, error_message)
        except Exception as error:
            self.logger.warning("更新视频任务记录失败: %s", error)
        self._active_video_task_id = None

    def _choose_directory(self) -> None:
        current = self.directory_edit.text().strip() or str(Path.home())
        directory = QFileDialog.getExistingDirectory(self, "选择图片保存目录", current)
        if directory:
            self.directory_edit.setText(directory)
            self._save_config()

    def _choose_video_directory(self) -> None:
        current = self.video_directory_edit.text().strip() or str(Path.home())
        directory = QFileDialog.getExistingDirectory(self, "选择视频输出目录", current)
        if directory:
            self.video_directory_edit.setText(directory)
            self._save_config()

    def _open_video_directory(self) -> None:
        directory = Path(self.video_directory_edit.text().strip())
        try:
            directory.mkdir(parents=True, exist_ok=True)
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(directory)))
        except OSError as error:
            self.logger.error("打开视频输出目录失败: %s", error)
            QMessageBox.warning(self, "无法打开目录", str(error))

    @staticmethod
    def _widget_date(editor: QDateEdit) -> date:
        value = editor.date()
        return date(value.year(), value.month(), value.day())


__all__ = ["VideoPlanIntegrationMixin"]
