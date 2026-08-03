"""Timelapse Studio 统一 SVG 图标工厂。"""

from __future__ import annotations

from PySide6.QtCore import QByteArray
from PySide6.QtGui import QIcon, QPainter, QPixmap
from PySide6.QtSvg import QSvgRenderer


_PATHS = {
    "home": '<path d="M3 10.5 12 3l9 7.5v9a1.5 1.5 0 0 1-1.5 1.5h-13A1.5 1.5 0 0 1 5 19.5v-9Z"/><path d="M9 21v-6h6v6"/>',
    "camera": '<rect x="3" y="6" width="18" height="14" rx="2"/><path d="m8 6 1.5-3h5L16 6"/><circle cx="12" cy="13" r="3.5"/>',
    "capture": '<circle cx="12" cy="12" r="8.5"/><path d="M12 7v5l3 2"/>',
    "video": '<rect x="3" y="5" width="14" height="14" rx="2"/><path d="m17 10 4-2v8l-4-2"/><path d="M8 9.5v5l4-2.5-4-2.5Z"/>',
    "folder": '<path d="M3 6.5A2.5 2.5 0 0 1 5.5 4H10l2 2h6.5A2.5 2.5 0 0 1 21 8.5v9a2.5 2.5 0 0 1-2.5 2.5h-13A2.5 2.5 0 0 1 3 17.5v-11Z"/>',
    "log": '<path d="M5 3.5h14v17H5z"/><path d="M8 8h8M8 12h8M8 16h5"/>',
    "settings": '<path d="M12 8.5a3.5 3.5 0 1 0 0 7 3.5 3.5 0 0 0 0-7Z"/><path d="m19.4 15 .1.1a2 2 0 0 1-2.8 2.8l-.1-.1a2 2 0 0 0-3.4 1.4v.2a2 2 0 0 1-4 0v-.2a2 2 0 0 0-3.4-1.4l-.1.1A2 2 0 0 1 3 15.1l.1-.1A2 2 0 0 0 1.7 11.6h-.2a2 2 0 0 1 0-4h.2A2 2 0 0 0 3 4.2l-.1-.1A2 2 0 0 1 5.7 1.3l.1.1a2 2 0 0 0 3.4-1.4v-.2a2 2 0 0 1 4 0V0a2 2 0 0 0 3.4 1.4l.1-.1a2 2 0 0 1 2.8 2.8l-.1.1A2 2 0 0 0 18.7 7h.2a2 2 0 0 1 0 4h-.2a2 2 0 0 0 .7 4Z" transform="translate(2 2) scale(.83)"/>',
    "refresh": '<path d="M20 11a8 8 0 0 0-14.5-4.6L4 8"/><path d="M4 4v4h4"/><path d="M4 13a8 8 0 0 0 14.5 4.6L20 16"/><path d="M20 20v-4h-4"/>',
    "play": '<path d="m8 5 10 7-10 7V5Z"/>',
    "stop": '<rect x="6" y="6" width="12" height="12" rx="1"/>',
    "plus": '<path d="M12 5v14M5 12h14"/>',
    "external": '<path d="M14 5h5v5M19 5l-8 8"/><path d="M18 13v5a1 1 0 0 1-1 1H6a1 1 0 0 1-1-1V7a1 1 0 0 1 1-1h5"/>',
}


def icon(name: str, color: str = "#64748b", size: int = 20) -> QIcon:
    """创建统一线性 SVG 图标。"""
    path = _PATHS.get(name, _PATHS["settings"])
    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">{path}</svg>"""
    renderer = QSvgRenderer(QByteArray(svg.encode("utf-8")))
    pixmap = QPixmap(size, size)
    pixmap.fill(0)
    painter = QPainter(pixmap)
    renderer.render(painter)
    painter.end()
    return QIcon(pixmap)


__all__ = ["icon"]
