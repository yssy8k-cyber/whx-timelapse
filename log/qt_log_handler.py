"""将 Python logging 转发到 Qt 日志窗口。"""

from __future__ import annotations

import logging

from PySide6.QtCore import QObject, Signal


class QtLogHandler(QObject, logging.Handler):
    """线程安全地把日志记录转换为 Qt 信号。"""

    message_emitted = Signal(str)

    def __init__(self) -> None:
        QObject.__init__(self)
        logging.Handler.__init__(self)

    def emit(self, record: logging.LogRecord) -> None:
        try:
            self.message_emitted.emit(self.format(record))
        except RuntimeError:
            # Qt 对象销毁后，异步日志可能仍有一条收尾消息到达。
            # 此时丢弃界面消息，不能让日志线程打印二次异常。
            return
        except Exception:
            self.handleError(record)
