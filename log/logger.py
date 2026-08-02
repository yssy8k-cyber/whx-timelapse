"""异步日志队列和滚动文件日志配置。"""

from __future__ import annotations

import logging
from logging import Handler, Logger
from logging.handlers import (
    QueueHandler,
    QueueListener,
    RotatingFileHandler,
)
from pathlib import Path
from queue import Queue


LOG_FORMAT = "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
RUNTIME_ATTRIBUTE = "_timelapse_logging_runtime"


class LoggingRuntime:
    """封装日志队列、后台监听线程和输出处理器。"""

    def __init__(self, logger: Logger, log_dir: Path) -> None:
        self.logger = logger
        self.queue: Queue[logging.LogRecord] = Queue()
        self.queue_handler = QueueHandler(self.queue)
        formatter = logging.Formatter(LOG_FORMAT)
        self.file_handler = RotatingFileHandler(
            log_dir / "timelapse_studio.log",
            maxBytes=5 * 1024 * 1024,
            backupCount=3,
            encoding="utf-8",
        )
        self.file_handler.setFormatter(formatter)
        self.console_handler = logging.StreamHandler()
        self.console_handler.setFormatter(formatter)
        self.listener = QueueListener(
            self.queue,
            self.file_handler,
            self.console_handler,
            respect_handler_level=True,
        )
        self.logger.addHandler(self.queue_handler)
        self.listener.start()

    def add_handler(self, handler: Handler) -> None:
        """将额外处理器接入日志线程。"""
        if handler not in self.listener.handlers:
            self.listener.handlers = (*self.listener.handlers, handler)

    def stop(self) -> None:
        """停止监听线程并关闭所有输出处理器。"""
        self.listener.stop()
        for handler in self.listener.handlers:
            handler.close()
        self.queue_handler.close()


def configure_logging(log_dir: Path) -> Logger:
    """创建异步文件、控制台日志，并返回应用 logger。"""
    log_dir.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger("timelapse_studio")
    logger.setLevel(logging.INFO)
    logger.propagate = False
    if getattr(logger, RUNTIME_ATTRIBUTE, None) is not None:
        return logger

    runtime = LoggingRuntime(logger, log_dir)
    setattr(logger, RUNTIME_ATTRIBUTE, runtime)
    return logger


def add_log_handler(logger: Logger, handler: Handler) -> None:
    """将界面等额外处理器接入应用日志线程。"""
    runtime: LoggingRuntime | None = getattr(logger, RUNTIME_ATTRIBUTE, None)
    if runtime is None:
        logger.addHandler(handler)
        return
    runtime.add_handler(handler)


def shutdown_logging(logger: Logger) -> None:
    """停止应用日志线程，支持进程重复初始化日志。"""
    runtime: LoggingRuntime | None = getattr(logger, RUNTIME_ATTRIBUTE, None)
    if runtime is None:
        return
    runtime.stop()
    logger.removeHandler(runtime.queue_handler)
    delattr(logger, RUNTIME_ATTRIBUTE)
