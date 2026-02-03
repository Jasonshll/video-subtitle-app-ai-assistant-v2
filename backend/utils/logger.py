"""日志工具模块"""

import logging
import sys
from pathlib import Path
from datetime import datetime
from logging.handlers import RotatingFileHandler


class ColoredFormatter(logging.Formatter):
    """带颜色的日志格式化器"""

    COLORS = {
        "DEBUG": "\033[36m",  # Cyan
        "INFO": "\033[32m",  # Green
        "WARNING": "\033[33m",  # Yellow
        "ERROR": "\033[31m",  # Red
        "CRITICAL": "\033[35m",  # Magenta
    }
    RESET = "\033[0m"

    def format(self, record):
        log_color = self.COLORS.get(record.levelname, self.RESET)
        record.levelname = f"{log_color}{record.levelname}{self.RESET}"
        return super().format(record)


class LoggerManager:
    """日志管理器单例"""

    _instance = None
    _loggers = {}

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        self.log_dir = Path(__file__).parent.parent / "logs"
        self.log_dir.mkdir(exist_ok=True)
        self.default_level = logging.INFO
        self.max_bytes = 10 * 1024 * 1024  # 10MB
        self.backup_count = 5

    def setup_logger(
        self, name: str, level: int = None, log_to_file: bool = True
    ) -> logging.Logger:
        """设置并获取日志记录器"""
        if name in self._loggers:
            return self._loggers[name]

        logger = logging.getLogger(name)

        # 避免重复添加处理器
        if logger.handlers:
            return logger

        level = level or self.default_level
        logger.setLevel(level)
        logger.propagate = False

        # 控制台处理器（带颜色）
        # 在 Windows 上，显式设置编码为 utf-8
        try:
            import io
            if sys.stdout.encoding.lower() != 'utf-8':
                sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
        except:
            pass

        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(level)
        console_format = ColoredFormatter(
            "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        console_handler.setFormatter(console_format)
        logger.addHandler(console_handler)

        # 文件处理器（无颜色）
        if log_to_file:
            log_file = self.log_dir / f"{name}_{datetime.now().strftime('%Y%m%d')}.log"
            file_handler = RotatingFileHandler(
                log_file,
                maxBytes=self.max_bytes,
                backupCount=self.backup_count,
                encoding="utf-8",
            )
            file_handler.setLevel(level)
            file_format = logging.Formatter(
                "%(asctime)s | %(levelname)-8s | %(name)s | %(filename)s:%(lineno)d | %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S",
            )
            file_handler.setFormatter(file_format)
            logger.addHandler(file_handler)

        self._loggers[name] = logger
        return logger

    def get_logger(self, name: str) -> logging.Logger:
        """获取已配置的日志记录器"""
        if name not in self._loggers:
            return self.setup_logger(name)
        return self._loggers[name]


# 全局日志管理器实例
_logger_manager = LoggerManager()


def setup_logger(
    name: str, level: int = None, log_to_file: bool = True
) -> logging.Logger:
    """设置日志记录器"""
    return _logger_manager.setup_logger(name, level, log_to_file)


def get_logger(name: str) -> logging.Logger:
    """获取日志记录器"""
    return _logger_manager.get_logger(name)
