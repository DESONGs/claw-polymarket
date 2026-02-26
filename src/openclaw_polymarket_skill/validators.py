from __future__ import annotations

import re
from typing import Any


TOKEN_ID_RE = re.compile(r"^[0-9]{1,100}$")
CONDITION_ID_RE = re.compile(r"^0x[0-9a-fA-F]{64}$")
ADDRESS_RE = re.compile(r"^0x[0-9a-fA-F]{40}$")
ORDER_ID_RE = re.compile(r"^[0-9a-zA-Z_-]{1,128}$")
ORDER_IDS_RE = re.compile(r"^[0-9a-zA-Z_-]{1,128}(,[0-9a-zA-Z_-]{1,128})*$")
SLUG_RE = re.compile(r"^[a-z0-9-]{1,200}$")
DECIMAL_RE = re.compile(r"^[0-9]+(\.[0-9]+)?$")
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def validate_presence(params: dict[str, Any], required_params: tuple[str, ...]) -> str | None:
    for key in required_params:
        if key not in params or params[key] is None:
            return f"缺少必填参数: {key}"
    return None


def validate_param(name: str, value: Any) -> str | None:
    if value is None:
        return None

    v = str(value)

    if name in {"token_id", "token"} and not TOKEN_ID_RE.fullmatch(v):
        return f"{name} 必须是纯数字字符串"
    if name in {"condition_id", "market"} and not CONDITION_ID_RE.fullmatch(v):
        return f"{name} 必须是 0x 开头的 64 位十六进制"
    if name == "address" and not ADDRESS_RE.fullmatch(v):
        return "address 必须是 0x 开头的 40 位十六进制"
    if name == "order_id" and not ORDER_ID_RE.fullmatch(v):
        return "order_id 格式不合法"
    if name == "order_ids" and not ORDER_IDS_RE.fullmatch(v):
        return "order_ids 必须是逗号分隔的 order_id 列表"
    if name == "asset_type" and v not in {"collateral", "conditional"}:
        return "asset_type 仅支持 collateral 或 conditional"
    if name == "side" and v not in {"buy", "sell"}:
        return "side 仅支持 buy 或 sell"
    if name == "order_type" and v not in {"GTC", "FOK", "GTD", "FAK"}:
        return "order_type 仅支持 GTC/FOK/GTD/FAK"
    if name == "interval" and v not in {"1m", "1h", "6h", "1d", "1w", "max"}:
        return "interval 仅支持 1m/1h/6h/1d/1w/max"
    if name in {"price", "size", "amount"}:
        if not DECIMAL_RE.fullmatch(v):
            return f"{name} 必须是正十进制数字"
        numeric = float(v)
        if numeric <= 0:
            return f"{name} 必须大于 0"
        if name == "price" and numeric >= 1:
            return "price 必须小于 1"
    if name == "query":
        if len(v.strip()) == 0 or len(v) > 200:
            return "query 长度必须在 1-200 之间"
    if name == "limit":
        try:
            numeric = int(v)
        except ValueError:
            return "limit 必须是整数"
        if numeric < 1 or numeric > 100:
            return "limit 范围必须在 1-100"
    if name == "offset":
        try:
            numeric = int(v)
        except ValueError:
            return "offset 必须是整数"
        if numeric < 0:
            return "offset 不能小于 0"
    if name == "slug" and not SLUG_RE.fullmatch(v):
        return "slug 仅支持小写字母、数字和中划线"
    if name == "date" and not DATE_RE.fullmatch(v):
        return "date 必须是 YYYY-MM-DD 格式"

    return None
