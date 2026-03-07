from __future__ import annotations

import asyncio
import time
from typing import Any

from .analyze_models import MarketSnapshot, TokenData
from .runner import PolymarketSkillRunner
from .settings import SkillSettings


class MarketCollector:
    """编排多个现有 action，并行采集市场数据"""

    def __init__(self, settings: SkillSettings | None = None) -> None:
        self._settings = settings or SkillSettings.from_env()
        self._runner = PolymarketSkillRunner(settings=self._settings)

    async def collect(self, query: str, market_limit: int = 5) -> MarketSnapshot:
        snapshot = MarketSnapshot(query=query)
        actions_called = 0

        # 阶段1：搜索市场列表
        search_result = await self._runner.execute("markets_search", {"query": query, "limit": market_limit})
        actions_called += 1

        markets: list[dict[str, Any]] = []
        if search_result.get("ok"):
            raw = search_result.get("data") or {}
            markets = raw.get("markets") or raw.get("results") or []
            if isinstance(markets, list):
                markets = markets[:market_limit]
        else:
            error_msg = (search_result.get("error") or {}).get("message", "markets_search 失败")
            snapshot.fetch_errors.append(f"markets_search: {error_msg}")

        snapshot.markets = markets

        # 阶段2：对每个市场并行采集 token 数据
        all_token_ids: list[str] = []
        for market in markets:
            token_ids = market.get("clobTokenIds") or []
            all_token_ids.extend(str(t) for t in token_ids if t)

        if all_token_ids:
            token_tasks = [self._collect_token(tid) for tid in all_token_ids]
            token_results = await asyncio.gather(*token_tasks, return_exceptions=True)
            actions_called += len(all_token_ids) * 4  # midpoint/spread/book/history

            for tid, result in zip(all_token_ids, token_results):
                if isinstance(result, Exception):
                    snapshot.fetch_errors.append(f"token {tid}: {result}")
                else:
                    td, errs = result
                    snapshot.token_data.append(td)
                    snapshot.fetch_errors.extend(errs)

        # 阶段3（可选）：采集相关事件
        try:
            events_result = await self._runner.execute("events_list", {})
            actions_called += 1
            if events_result.get("ok"):
                raw_events = events_result.get("data") or {}
                snapshot.events = (
                    raw_events.get("events")
                    or raw_events.get("results")
                    or []
                )[:10]
        except Exception as exc:  # noqa: BLE001
            snapshot.fetch_errors.append(f"events_list: {exc}")

        snapshot.actions_called = actions_called
        return snapshot

    async def _collect_token(self, token_id: str) -> tuple[TokenData, list[str]]:
        """并行采集单个 token 的 midpoint/spread/book/history"""
        td = TokenData(token_id=token_id)
        errors: list[str] = []

        async def _safe(action: str, params: dict[str, Any]) -> Any:
            try:
                result = await self._runner.execute(action, params)
                if result.get("ok"):
                    return result.get("data")
                errors.append(f"{action}({token_id}): {(result.get('error') or {}).get('message', '失败')}")
            except Exception as exc:  # noqa: BLE001
                errors.append(f"{action}({token_id}): {exc}")
            return None

        midpoint_data, spread_data, book_data, history_data = await asyncio.gather(
            _safe("clob_midpoint", {"token_id": token_id}),
            _safe("clob_spread", {"token_id": token_id}),
            _safe("clob_book", {"token_id": token_id}),
            _safe("clob_price_history", {"token_id": token_id}),
        )

        if midpoint_data is not None:
            td.midpoint = _extract_float(midpoint_data, "mid") or _extract_float(midpoint_data, "midpoint")

        if spread_data is not None:
            td.spread = _extract_float(spread_data, "spread") or _extract_float(spread_data, "ask_spread")

        if book_data is not None:
            td.book = book_data if isinstance(book_data, dict) else None

        if history_data is not None:
            if isinstance(history_data, list):
                td.price_history = history_data
            elif isinstance(history_data, dict):
                td.price_history = history_data.get("history") or history_data.get("prices")

        return td, errors


def _extract_float(data: Any, key: str) -> float | None:
    if isinstance(data, dict):
        val = data.get(key)
        if val is not None:
            try:
                return float(val)
            except (TypeError, ValueError):
                pass
    return None
