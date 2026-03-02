"""
结构化日志配置模块
"""
from __future__ import annotations

import json
import logging
import sys
from typing import Any, Dict


class StructuredFormatter(logging.Formatter):
    """JSON 格式的结构化日志"""

    def format(self, record: logging.LogRecord) -> str:
        log_data = {
            "timestamp": self.formatTime(record),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno
        }

        # 添加额外字段
        if hasattr(record, "extra_fields"):
            log_data.update(record.extra_fields)

        # 添加异常信息
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_data, ensure_ascii=False)


class ExtraFieldsAdapter(logging.LoggerAdapter):
    """支持额外字段的日志适配器"""

    def process(self, msg: str, kwargs: Any) -> tuple[str, Dict[str, Any]]:
        extra = kwargs.get("extra", {})
        if "extra_fields" not in extra and extra:
            extra["extra_fields"] = extra.copy()
        kwargs["extra"] = extra
        return msg, kwargs


def setup_logging(
    name: str = "openclaw_polymarket_skill",
    level: str = "INFO",
    use_json: bool = False
) -> logging.Logger:
    """
    配置日志系统

    Args:
        name: Logger 名称
        level: 日志级别 (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        use_json: 是否使用 JSON 格式

    Returns:
        配置好的 Logger 对象
    """
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, level.upper()))

    # 避免重复添加 handler
    if logger.handlers:
        return logger

    handler = logging.StreamHandler(sys.stdout)

    if use_json:
        handler.setFormatter(StructuredFormatter())
    else:
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        handler.setFormatter(formatter)

    logger.addHandler(handler)
    return logger


def get_logger(name: str | None = None) -> logging.Logger:
    """
    获取 Logger 实例

    Args:
        name: Logger 名称，默认使用模块名

    Returns:
        Logger 对象
    """
    if name is None:
        name = "openclaw_polymarket_skill"
    return logging.getLogger(name)
