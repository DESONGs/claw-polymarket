from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import Any

from .settings import SkillSettings

SENSITIVE_FLAGS = {"--private-key"}
PLACEHOLDER_MARKERS = ("__PLACEHOLDER__", "__OPENCLAW_", "0x" + ("0" * 64))


def sanitize_cmd(command: list[str]) -> list[str]:
    sanitized: list[str] = []
    mask_next = False
    for arg in command:
        if mask_next:
            sanitized.append("***REDACTED***")
            mask_next = False
            continue
        sanitized.append(arg)
        if arg in SENSITIVE_FLAGS:
            mask_next = True
    return sanitized


def is_placeholder_key(private_key: str | None, settings: SkillSettings) -> bool:
    if not private_key:
        return True
    value = private_key.strip()
    if len(value) < 10:
        return True
    if settings.placeholder_private_key and settings.placeholder_private_key in value:
        return True
    return any(marker in value for marker in PLACEHOLDER_MARKERS)


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
