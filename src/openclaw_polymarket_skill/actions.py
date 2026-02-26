from __future__ import annotations

from typing import Any

from .models import ActionCategory, ActionSpec


def _text(value: Any) -> str:
    return str(value)


def _bool_text(value: Any) -> str:
    return "true" if bool(value) else "false"


def _add_opt(args: list[str], params: dict[str, Any], key: str, flag: str) -> None:
    if key in params and params[key] is not None:
        args.extend([flag, _text(params[key])])


def _add_opt_bool(args: list[str], params: dict[str, Any], key: str, flag: str) -> None:
    if key in params and params[key] is not None:
        args.extend([flag, _bool_text(params[key])])


def build_markets_search(params: dict[str, Any]) -> list[str]:
    args = ["markets", "search", _text(params["query"])]
    args.extend(["--limit", _text(params.get("limit", 10))])
    return args


def build_markets_get(params: dict[str, Any]) -> list[str]:
    return ["markets", "get", _text(params["id_or_slug"])]


def build_markets_list(params: dict[str, Any]) -> list[str]:
    args = ["markets", "list", "--limit", _text(params.get("limit", 25))]
    _add_opt(args, params, "offset", "--offset")
    _add_opt_bool(args, params, "active", "--active")
    _add_opt_bool(args, params, "closed", "--closed")
    _add_opt(args, params, "order", "--order")
    if params.get("ascending") is True:
        args.append("--ascending")
    return args


def build_events_list(params: dict[str, Any]) -> list[str]:
    args = ["events", "list", "--limit", _text(params.get("limit", 25))]
    _add_opt(args, params, "tag", "--tag")
    _add_opt_bool(args, params, "active", "--active")
    _add_opt_bool(args, params, "closed", "--closed")
    _add_opt(args, params, "order", "--order")
    if params.get("ascending") is True:
        args.append("--ascending")
    return args


def build_events_get(params: dict[str, Any]) -> list[str]:
    return ["events", "get", _text(params["id"])]


def build_clob_book(params: dict[str, Any]) -> list[str]:
    return ["clob", "book", _text(params["token_id"])]


def build_clob_midpoint(params: dict[str, Any]) -> list[str]:
    return ["clob", "midpoint", _text(params["token_id"])]


def build_clob_spread(params: dict[str, Any]) -> list[str]:
    args = ["clob", "spread", _text(params["token_id"])]
    _add_opt(args, params, "side", "--side")
    return args


def build_clob_price(params: dict[str, Any]) -> list[str]:
    return ["clob", "price", _text(params["token_id"]), "--side", _text(params["side"])]


def build_clob_price_history(params: dict[str, Any]) -> list[str]:
    args = [
        "clob",
        "price-history",
        _text(params["token_id"]),
        "--interval",
        _text(params.get("interval", "1d")),
    ]
    _add_opt(args, params, "fidelity", "--fidelity")
    return args


def build_clob_balance(params: dict[str, Any]) -> list[str]:
    args = ["clob", "balance", "--asset-type", _text(params["asset_type"])]
    _add_opt(args, params, "token", "--token")
    return args


def build_clob_orders(params: dict[str, Any]) -> list[str]:
    args = ["clob", "orders"]
    _add_opt(args, params, "market", "--market")
    _add_opt(args, params, "asset", "--asset")
    _add_opt(args, params, "cursor", "--cursor")
    return args


def build_clob_order(params: dict[str, Any]) -> list[str]:
    return ["clob", "order", _text(params["order_id"])]


def build_clob_create_order(params: dict[str, Any]) -> list[str]:
    args = [
        "clob",
        "create-order",
        "--token",
        _text(params["token"]),
        "--side",
        _text(params["side"]),
        "--price",
        _text(params["price"]),
        "--size",
        _text(params["size"]),
        "--order-type",
        _text(params.get("order_type", "GTC")),
    ]
    if params.get("post_only") is True:
        args.append("--post-only")
    return args


def build_clob_market_order(params: dict[str, Any]) -> list[str]:
    return [
        "clob",
        "market-order",
        "--token",
        _text(params["token"]),
        "--side",
        _text(params["side"]),
        "--amount",
        _text(params["amount"]),
        "--order-type",
        _text(params.get("order_type", "FOK")),
    ]


def build_clob_cancel(params: dict[str, Any]) -> list[str]:
    return ["clob", "cancel", _text(params["order_id"])]


def build_clob_cancel_orders(params: dict[str, Any]) -> list[str]:
    return ["clob", "cancel-orders", _text(params["order_ids"])]


def build_clob_cancel_all(_: dict[str, Any]) -> list[str]:
    return ["clob", "cancel-all"]


def build_data_positions(params: dict[str, Any]) -> list[str]:
    args = ["data", "positions", _text(params["address"]), "--limit", _text(params.get("limit", 25))]
    _add_opt(args, params, "offset", "--offset")
    return args


def build_data_value(params: dict[str, Any]) -> list[str]:
    return ["data", "value", _text(params["address"])]


def build_data_trades(params: dict[str, Any]) -> list[str]:
    args = ["data", "trades", _text(params["address"]), "--limit", _text(params.get("limit", 25))]
    _add_opt(args, params, "offset", "--offset")
    return args


def build_data_leaderboard(params: dict[str, Any]) -> list[str]:
    args = ["data", "leaderboard", "--limit", _text(params.get("limit", 25))]
    _add_opt(args, params, "period", "--period")
    _add_opt(args, params, "order_by", "--order-by")
    _add_opt(args, params, "offset", "--offset")
    return args


ACTION_REGISTRY: dict[str, ActionSpec] = {
    "markets_search": ActionSpec("markets_search", ActionCategory.READ, ("query",), build_markets_search),
    "markets_get": ActionSpec("markets_get", ActionCategory.READ, ("id_or_slug",), build_markets_get),
    "markets_list": ActionSpec("markets_list", ActionCategory.READ, tuple(), build_markets_list),
    "events_list": ActionSpec("events_list", ActionCategory.READ, tuple(), build_events_list),
    "events_get": ActionSpec("events_get", ActionCategory.READ, ("id",), build_events_get),
    "clob_book": ActionSpec("clob_book", ActionCategory.READ, ("token_id",), build_clob_book),
    "clob_midpoint": ActionSpec("clob_midpoint", ActionCategory.READ, ("token_id",), build_clob_midpoint),
    "clob_spread": ActionSpec("clob_spread", ActionCategory.READ, ("token_id",), build_clob_spread),
    "clob_price": ActionSpec("clob_price", ActionCategory.READ, ("token_id", "side"), build_clob_price),
    "clob_price_history": ActionSpec("clob_price_history", ActionCategory.READ, ("token_id",), build_clob_price_history),
    "clob_balance": ActionSpec("clob_balance", ActionCategory.READ_AUTH, ("asset_type",), build_clob_balance),
    "clob_orders": ActionSpec("clob_orders", ActionCategory.READ_AUTH, tuple(), build_clob_orders),
    "clob_order": ActionSpec("clob_order", ActionCategory.READ_AUTH, ("order_id",), build_clob_order),
    "clob_create_order": ActionSpec(
        "clob_create_order",
        ActionCategory.WRITE,
        ("token", "side", "price", "size"),
        build_clob_create_order,
    ),
    "clob_market_order": ActionSpec(
        "clob_market_order",
        ActionCategory.WRITE,
        ("token", "side", "amount"),
        build_clob_market_order,
    ),
    "clob_cancel": ActionSpec("clob_cancel", ActionCategory.WRITE, ("order_id",), build_clob_cancel),
    "clob_cancel_orders": ActionSpec("clob_cancel_orders", ActionCategory.WRITE, ("order_ids",), build_clob_cancel_orders),
    "clob_cancel_all": ActionSpec("clob_cancel_all", ActionCategory.WRITE, tuple(), build_clob_cancel_all),
    "data_positions": ActionSpec("data_positions", ActionCategory.READ, ("address",), build_data_positions),
    "data_value": ActionSpec("data_value", ActionCategory.READ, ("address",), build_data_value),
    "data_trades": ActionSpec("data_trades", ActionCategory.READ, ("address",), build_data_trades),
    "data_leaderboard": ActionSpec("data_leaderboard", ActionCategory.READ, tuple(), build_data_leaderboard),
}
