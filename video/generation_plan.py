"""视频生成计划中的日期范围、命名和输出文件策略。"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path


RANGE_TODAY = "today"
RANGE_YESTERDAY = "yesterday"
RANGE_LAST_24_HOURS = "last_24_hours"
RANGE_LAST_7_DAYS = "last_7_days"
RANGE_CUSTOM = "custom"


@dataclass(frozen=True)
class DateRange:
    """待生成的自然日期范围。"""

    start: date
    end: date
    start_datetime: datetime | None = None
    end_datetime: datetime | None = None

    def __post_init__(self) -> None:
        if self.start > self.end:
            raise ValueError("生成开始日期不能晚于结束日期")


def resolve_date_range(
    range_mode: str,
    now: datetime | None = None,
    custom_start: date | None = None,
    custom_end: date | None = None,
) -> DateRange:
    """根据计划选项计算自然日期范围。"""
    current_date = (now or datetime.now()).date()
    if range_mode == RANGE_TODAY:
        return DateRange(current_date, current_date)
    if range_mode == RANGE_YESTERDAY:
        yesterday = current_date - timedelta(days=1)
        return DateRange(yesterday, yesterday)
    if range_mode == RANGE_LAST_24_HOURS:
        end_datetime = (now or datetime.now()).replace(tzinfo=None)
        return DateRange(
            current_date - timedelta(days=1),
            current_date,
            start_datetime=end_datetime - timedelta(hours=24),
            end_datetime=end_datetime,
        )
    if range_mode == RANGE_LAST_7_DAYS:
        return DateRange(current_date - timedelta(days=6), current_date)
    if range_mode == RANGE_CUSTOM and custom_start and custom_end:
        return DateRange(custom_start, custom_end)
    raise ValueError("自定义生成范围必须填写开始日期和结束日期")


def image_directories(image_root: Path, date_range: DateRange) -> list[Path]:
    """将日期范围转换为按日期排列的图片目录列表。"""
    return [
        image_root / (date_range.start + timedelta(days=offset)).isoformat()
        for offset in range((date_range.end - date_range.start).days + 1)
    ]


def render_filename(
    template: str,
    camera_name: str,
    date_range: DateRange,
    now: datetime | None = None,
) -> str:
    """渲染文件名模板，并阻止模板产生目录穿越。"""
    current = now or datetime.now()
    date_text = date_range.start.isoformat()
    if date_range.start != date_range.end:
        date_text = f"{date_range.start.isoformat()}_to_{date_range.end.isoformat()}"
    values = {
        "date": date_text,
        "time": current.strftime("%H%M%S"),
        "camera": _safe_filename_part(camera_name),
    }
    try:
        filename = template.format(**values)
    except (KeyError, ValueError):
        filename = "Timelapse_{date}.mp4".format(**values)
    filename = _safe_filename_part(Path(filename).name)
    if not filename.lower().endswith(".mp4"):
        filename = f"{filename}.mp4"
    return filename


def _safe_filename_part(value: str) -> str:
    """清理 Windows 文件名非法字符。"""
    cleaned = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", value).strip(" .")
    return cleaned or "Timelapse"


__all__ = [
    "DateRange",
    "RANGE_CUSTOM",
    "RANGE_LAST_24_HOURS",
    "RANGE_LAST_7_DAYS",
    "RANGE_TODAY",
    "RANGE_YESTERDAY",
    "image_directories",
    "render_filename",
    "resolve_date_range",
]
