from __future__ import annotations

import argparse
import asyncio
import json
import time
from typing import Any

from .actions import ACTION_REGISTRY
from .analyze_models import AnalysisResult
from .claude_client import ClaudeClient
from .market_collector import MarketCollector
from .openclaw_bridge import serve_stdio
from .report_builder import OutputFormat, build_output
from .runner import PolymarketSkillRunner
from .settings import SkillSettings


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


async def _run_analyze(args: argparse.Namespace) -> int:
    settings = SkillSettings.from_env()

    if not settings.anthropic_api_key:
        print(
            json.dumps(
                {"ok": False, "error": "ANTHROPIC_API_KEY 未配置，analyze 命令需要 Claude API key"},
                ensure_ascii=False,
            )
        )
        return 2

    market_limit: int = getattr(args, "market_limit", 5)
    output_fmt: OutputFormat = getattr(args, "output", "both")

    collector = MarketCollector(settings=settings)
    snapshot = await collector.collect(args.query, market_limit=market_limit)

    claude = ClaudeClient(settings=settings)
    result = claude.analyze(snapshot, args.analysis_prompt)

    output = build_output(result, fmt=output_fmt)
    print(output)
    return 0 if result.ok else 1


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

    analyze = sub.add_parser("analyze", help="一键采集市场数据并调用 Claude 进行 AI 分析")
    analyze.add_argument("--query", required=True, help="搜索关键词")
    analyze.add_argument("--analysis-prompt", required=True, dest="analysis_prompt", help="分析提示词（传给 Claude）")
    analyze.add_argument("--market-limit", type=int, default=5, dest="market_limit", help="最多分析的市场数量（默认 5）")
    analyze.add_argument(
        "--output",
        choices=["json", "markdown", "both"],
        default="both",
        help="输出格式（默认 both）",
    )
    analyze.set_defaults(handler=lambda ns: asyncio.run(_run_analyze(ns)))

    args = parser.parse_args()
    exit_code = args.handler(args)
    raise SystemExit(exit_code)


if __name__ == "__main__":
    main()
