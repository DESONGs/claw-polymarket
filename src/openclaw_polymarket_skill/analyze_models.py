from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class TokenData:
    """单个 token 的市场行情数据"""

    token_id: str
    midpoint: float | None = None
    spread: float | None = None
    book: dict[str, Any] | None = None
    price_history: list[dict[str, Any]] | None = None


@dataclass
class MarketSnapshot:
    """某查询词下所有市场的快照数据"""

    query: str
    markets: list[dict[str, Any]] = field(default_factory=list)
    token_data: list[TokenData] = field(default_factory=list)
    events: list[dict[str, Any]] = field(default_factory=list)
    fetch_errors: list[str] = field(default_factory=list)
    actions_called: int = 0

    def to_summary_dict(self) -> dict[str, Any]:
        """返回去除原始委托簿明细的精简摘要，供 Claude 分析用"""
        market_summaries = []
        for market in self.markets:
            market_id = market.get("conditionId") or market.get("id", "")
            token_ids = market.get("clobTokenIds") or []
            token_summaries = []
            for td in self.token_data:
                if td.token_id not in token_ids:
                    continue
                book_summary: dict[str, Any] | None = None
                if td.book:
                    bids = td.book.get("bids") or []
                    asks = td.book.get("asks") or []
                    book_summary = {
                        "bid_levels": len(bids),
                        "ask_levels": len(asks),
                        "best_bid": bids[0] if bids else None,
                        "best_ask": asks[0] if asks else None,
                    }
                history_summary: dict[str, Any] | None = None
                if td.price_history:
                    prices = [p.get("p") for p in td.price_history if "p" in p]
                    if prices:
                        history_summary = {
                            "data_points": len(prices),
                            "min_price": min(prices),
                            "max_price": max(prices),
                            "last_price": prices[-1],
                        }
                token_summaries.append(
                    {
                        "token_id": td.token_id,
                        "midpoint": td.midpoint,
                        "spread": td.spread,
                        "book_summary": book_summary,
                        "price_history_summary": history_summary,
                    }
                )
            market_summaries.append(
                {
                    "id": market_id,
                    "question": market.get("question", ""),
                    "slug": market.get("slug", ""),
                    "active": market.get("active"),
                    "volume": market.get("volume"),
                    "tokens": token_summaries,
                }
            )
        return {
            "query": self.query,
            "market_count": len(self.markets),
            "markets": market_summaries,
            "events": self.events,
            "fetch_errors": self.fetch_errors,
        }


@dataclass
class AnalysisResult:
    """完整的分析结果，含结构化数据和 Markdown 报告"""

    ok: bool
    query: str
    markets_analyzed: int
    structured: dict[str, Any] = field(default_factory=dict)
    report_markdown: str = ""
    raw_market_data: list[dict[str, Any]] = field(default_factory=list)
    error: str | None = None
    meta: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {
            "ok": self.ok,
            "query": self.query,
            "markets_analyzed": self.markets_analyzed,
            "structured": self.structured,
            "report_markdown": self.report_markdown,
            "raw_market_data": self.raw_market_data,
            "meta": self.meta,
        }
        if self.error:
            result["error"] = self.error
        return result
