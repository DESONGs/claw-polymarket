from __future__ import annotations

import argparse
import asyncio
import json
from typing import Any

from .actions import ACTION_REGISTRY
from .openclaw_bridge import serve_stdio
from .runner import PolymarketSkillRunner


def _parse_json(value: str, name: str) -> dict[str, Any]:
    if not value:
        return {}
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError as exc:
        raise ValueError(f"{name} 不是合法 JSON: {exc}") from exc
    if not isinstance(parsed, dict):
        raise ValueError(f"{name} 必须是 JSON 对象")
    return parsed


async def _run_execute(args: argparse.Namespace) -> int:
    runner = PolymarketSkillRunner()
    try:
        params = _parse_json(args.params, "--params")
        context = _parse_json(args.context, "--context")
    except ValueError as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False))
        return 2

    result = await runner.execute(args.action, params=params, context=context)
    print(json.dumps(result, ensure_ascii=False))
    return 0 if result.get("ok") else 1


async def _run_healthcheck() -> int:
    runner = PolymarketSkillRunner()
    result = await runner.healthcheck()
    print(json.dumps(result, ensure_ascii=False))
    return 0 if result.get("ok") else 1


def _run_list_actions() -> int:
    data = [
        {
            "name": spec.name,
            "category": spec.category.value,
            "required_params": list(spec.required_params),
        }
        for spec in ACTION_REGISTRY.values()
    ]
    print(json.dumps({"ok": True, "actions": data}, ensure_ascii=False))
    return 0


def main() -> None:
    parser = argparse.ArgumentParser(prog="openclaw-polymarket-skill", description="OpenClaw Polymarket Skill")
    sub = parser.add_subparsers(dest="command", required=True)

    list_actions = sub.add_parser("list-actions", help="列出支持的 actions")
    list_actions.set_defaults(handler=lambda _: _run_list_actions())

    healthcheck = sub.add_parser("healthcheck", help="检查 polymarket 二进制与版本")
    healthcheck.set_defaults(handler=lambda _: asyncio.run(_run_healthcheck()))

    execute = sub.add_parser("execute", help="执行 action")
    execute.add_argument("--action", required=True, help="action 名称")
    execute.add_argument("--params", default="{}", help="JSON 对象")
    execute.add_argument("--context", default="{}", help="JSON 对象")
    execute.set_defaults(handler=lambda ns: asyncio.run(_run_execute(ns)))

    bridge = sub.add_parser("serve-stdio", help="以 stdio bridge 模式运行，供 OpenClaw 直接调用")
    bridge.set_defaults(handler=lambda _: asyncio.run(serve_stdio()) or 0)

    args = parser.parse_args()
    exit_code = args.handler(args)
    raise SystemExit(exit_code)


if __name__ == "__main__":
    main()
