from __future__ import annotations

import re
from decimal import Decimal, InvalidOperation
from typing import Any, Optional

from .settings import SkillSettings

SENSITIVE_FLAGS = {
    "--private-key",
    "--api-key",
    "--secret",
    "--password",
    "--token"
}

PLACEHOLDER_PATTERNS = [
    r"^0x0{64}$",                    # 全零
    r"^0xf{64}$",                    # 全F
    r"^0x1{64}$",                    # 全1
    r"__PLACEHOLDER__",
    r"__OPENCLAW_",
    r"YOUR[_-]PRIVATE[_-]KEY",
    r"INSERT[_-]KEY[_-]HERE",
    r"TEST[_-]KEY",
    r"DEMO[_-]KEY"
]


def sanitize_cmd(command: list[str]) -> list[str]:
    """
    脱敏命令参数，支持两种格式:
    1. --flag value
    2. --flag=value

    Args:
        command: 原始命令参数列表

    Returns:
        脱敏后的命令参数列表
    """
    sanitized: list[str] = []
    mask_next = False

    for arg in command:
        # 处理 --flag=value 格式
        if "=" in arg:
            key_part, value_part = arg.split("=", 1)
            if key_part in SENSITIVE_FLAGS:
                sanitized.append(f"{key_part}=***REDACTED***")
                continue

        # 处理 --flag value 格式
        if mask_next:
            sanitized.append("***REDACTED***")
            mask_next = False
        elif arg in SENSITIVE_FLAGS:
            sanitized.append(arg)
            mask_next = True
        else:
            sanitized.append(arg)

    return sanitized


def is_valid_private_key(key: Optional[str]) -> bool:
    """
    验证私钥格式的有效性

    有效私钥要求:
    1. 非空字符串
    2. 0x + 64位十六进制字符
    3. 不匹配任何 placeholder 模式

    Args:
        key: 待验证的私钥

    Returns:
        True 如果私钥格式有效，否则 False
    """
    if not key or not isinstance(key, str):
        return False

    # 检查格式: 0x + 64个十六进制字符
    if not key.startswith("0x") or len(key) != 66:
        return False

    hex_part = key[2:]
    if not re.match(r"^[0-9a-fA-F]{64}$", hex_part):
        return False

    # 检查是否为 placeholder
    for pattern in PLACEHOLDER_PATTERNS:
        if re.search(pattern, key, re.IGNORECASE):
            return False

    return True


def is_placeholder_key(private_key: str | None, settings: SkillSettings) -> bool:
    """
    检查私钥是否为 placeholder（兼容旧接口）

    Args:
        private_key: 待检查的私钥
        settings: 配置对象

    Returns:
        True 如果是 placeholder，否则 False
    """
    if not private_key:
        return True

    # 使用新的验证逻辑
    if not is_valid_private_key(private_key):
        return True

    # 额外检查配置中的 placeholder
    value = private_key.strip()
    if settings.placeholder_private_key and settings.placeholder_private_key in value:
        return True

    return False


def estimate_amount(action: str, params: dict[str, Any]) -> Decimal | None:
    if action == "clob_create_order":
        try:
            return Decimal(str(params["price"])) * Decimal(str(params["size"]))
        except (KeyError, InvalidOperation):
            return None

    if action == "clob_market_order":
        side = str(params.get("side", "")).lower()
        if side == "buy":
            try:
                return Decimal(str(params["amount"]))
            except (KeyError, InvalidOperation):
                return None
    return None
