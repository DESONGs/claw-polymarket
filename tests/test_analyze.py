"""
分析工作流测试：MarketCollector、ClaudeClient、ReportBuilder
"""
from __future__ import annotations

import asyncio
import json
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from openclaw_polymarket_skill.analyze_models import AnalysisResult, MarketSnapshot, TokenData
from openclaw_polymarket_skill.market_collector import MarketCollector, _extract_float
from openclaw_polymarket_skill.settings import SkillSettings


# ---------------------------------------------------------------------------
# MarketSnapshot / TokenData 数据模型测试
# ---------------------------------------------------------------------------


def test_market_snapshot_defaults() -> None:
    snap = MarketSnapshot(query="test")
    assert snap.query == "test"
    assert snap.markets == []
    assert snap.token_data == []
    assert snap.fetch_errors == []
    assert snap.actions_called == 0


def test_token_data_defaults() -> None:
    td = TokenData(token_id="tok123")
    assert td.token_id == "tok123"
    assert td.midpoint is None
    assert td.spread is None


def test_market_snapshot_to_summary_dict_empty() -> None:
    snap = MarketSnapshot(query="btc")
    summary = snap.to_summary_dict()
    assert summary["query"] == "btc"
    assert summary["market_count"] == 0
    assert summary["markets"] == []


def test_market_snapshot_to_summary_dict_with_data() -> None:
    snap = MarketSnapshot(
        query="btc",
        markets=[
            {
                "conditionId": "0xabc",
                "question": "BTC > 100k?",
                "clobTokenIds": ["tok1"],
                "active": True,
                "volume": "50000",
            }
        ],
        token_data=[
            TokenData(
                token_id="tok1",
                midpoint=0.65,
                spread=0.02,
                book={"bids": [{"price": "0.64", "size": "100"}], "asks": [{"price": "0.66", "size": "80"}]},
                price_history=[{"p": 0.60}, {"p": 0.62}, {"p": 0.65}],
            )
        ],
    )
    summary = snap.to_summary_dict()
    assert summary["market_count"] == 1
    market = summary["markets"][0]
    assert market["id"] == "0xabc"
    assert market["question"] == "BTC > 100k?"
    token = market["tokens"][0]
    assert token["midpoint"] == 0.65
    assert token["spread"] == 0.02
    assert token["book_summary"]["bid_levels"] == 1
    assert token["price_history_summary"]["data_points"] == 3
    assert token["price_history_summary"]["last_price"] == 0.65


def test_analysis_result_to_dict_no_error() -> None:
    result = AnalysisResult(
        ok=True,
        query="q",
        markets_analyzed=2,
        structured={"overall_sentiment": "bullish"},
        report_markdown="# 报告",
        meta={"duration_ms": 1000},
    )
    d = result.to_dict()
    assert d["ok"] is True
    assert d["markets_analyzed"] == 2
    assert "error" not in d


def test_analysis_result_to_dict_with_error() -> None:
    result = AnalysisResult(ok=False, query="q", markets_analyzed=0, error="API key 缺失")
    d = result.to_dict()
    assert d["ok"] is False
    assert d["error"] == "API key 缺失"


# ---------------------------------------------------------------------------
# _extract_float 辅助函数测试
# ---------------------------------------------------------------------------


def test_extract_float_found() -> None:
    assert _extract_float({"mid": "0.65"}, "mid") == 0.65


def test_extract_float_not_found() -> None:
    assert _extract_float({"other": "0.65"}, "mid") is None


def test_extract_float_non_dict() -> None:
    assert _extract_float("0.65", "mid") is None


def test_extract_float_invalid_value() -> None:
    assert _extract_float({"mid": "not_a_float"}, "mid") is None


# ---------------------------------------------------------------------------
# MarketCollector 测试（使用 mock runner）
# ---------------------------------------------------------------------------


def _make_ok_result(data: Any) -> dict[str, Any]:
    return {"ok": True, "data": data}


def _make_fail_result(msg: str) -> dict[str, Any]:
    return {"ok": False, "error": {"message": msg, "type": "TestError", "retryable": False}}


@pytest.fixture
def no_version_check_settings() -> SkillSettings:
    return SkillSettings(enforce_cli_version=False)


def test_collector_empty_search_result(no_version_check_settings: SkillSettings) -> None:
    """搜索返回空列表时，snapshot 应正常但无 token 数据"""
    collector = MarketCollector(settings=no_version_check_settings)

    async def fake_execute(action: str, params: dict[str, Any] | None = None, context: dict[str, Any] | None = None) -> dict[str, Any]:
        if action == "markets_search":
            return _make_ok_result({"markets": []})
        if action == "events_list":
            return _make_ok_result({"events": []})
        return _make_fail_result("unexpected call")

    collector._runner.execute = fake_execute  # type: ignore[method-assign]
    snap = asyncio.run(collector.collect("no-results-query", market_limit=5))
    assert snap.query == "no-results-query"
    assert snap.markets == []
    assert snap.token_data == []
    assert snap.fetch_errors == []


def test_collector_search_failure_records_error(no_version_check_settings: SkillSettings) -> None:
    """搜索失败时，fetch_errors 应记录错误但不抛异常"""
    collector = MarketCollector(settings=no_version_check_settings)

    async def fake_execute(action: str, params: dict[str, Any] | None = None, context: dict[str, Any] | None = None) -> dict[str, Any]:
        if action == "markets_search":
            return _make_fail_result("network error")
        if action == "events_list":
            return _make_ok_result({"events": []})
        return _make_fail_result("unexpected")

    collector._runner.execute = fake_execute  # type: ignore[method-assign]
    snap = asyncio.run(collector.collect("fail-query"))
    assert len(snap.fetch_errors) == 1
    assert "markets_search" in snap.fetch_errors[0]


def test_collector_collects_token_data(no_version_check_settings: SkillSettings) -> None:
    """正常流程：搜索到1个市场1个token，4个CLOB action均成功"""
    collector = MarketCollector(settings=no_version_check_settings)
    call_count: dict[str, int] = {}

    async def fake_execute(action: str, params: dict[str, Any] | None = None, context: dict[str, Any] | None = None) -> dict[str, Any]:
        call_count[action] = call_count.get(action, 0) + 1
        if action == "markets_search":
            return _make_ok_result({
                "markets": [
                    {"conditionId": "0xmkt1", "question": "Q1?", "clobTokenIds": ["tok_yes"]}
                ]
            })
        if action == "clob_midpoint":
            return _make_ok_result({"mid": "0.65"})
        if action == "clob_spread":
            return _make_ok_result({"spread": "0.02"})
        if action == "clob_book":
            return _make_ok_result({"bids": [], "asks": []})
        if action == "clob_price_history":
            return _make_ok_result([{"p": 0.63}, {"p": 0.65}])
        if action == "events_list":
            return _make_ok_result({"events": []})
        return _make_fail_result("unexpected")

    collector._runner.execute = fake_execute  # type: ignore[method-assign]
    snap = asyncio.run(collector.collect("btc", market_limit=1))

    assert len(snap.markets) == 1
    assert len(snap.token_data) == 1
    td = snap.token_data[0]
    assert td.token_id == "tok_yes"
    assert td.midpoint == 0.65
    assert td.spread == 0.02
    assert td.book == {"bids": [], "asks": []}
    assert snap.fetch_errors == []


def test_collector_partial_token_failure(no_version_check_settings: SkillSettings) -> None:
    """部分 token action 失败时，其他数据仍能采集，错误记录到 fetch_errors"""
    collector = MarketCollector(settings=no_version_check_settings)

    async def fake_execute(action: str, params: dict[str, Any] | None = None, context: dict[str, Any] | None = None) -> dict[str, Any]:
        if action == "markets_search":
            return _make_ok_result({
                "markets": [{"conditionId": "0xm", "question": "Q?", "clobTokenIds": ["tok1"]}]
            })
        if action == "clob_midpoint":
            return _make_ok_result({"mid": "0.70"})
        if action == "clob_spread":
            return _make_fail_result("spread unavailable")
        if action == "clob_book":
            return _make_fail_result("book unavailable")
        if action == "clob_price_history":
            return _make_ok_result([{"p": 0.70}])
        if action == "events_list":
            return _make_ok_result({"events": []})
        return _make_fail_result("unexpected")

    collector._runner.execute = fake_execute  # type: ignore[method-assign]
    snap = asyncio.run(collector.collect("partial", market_limit=1))

    assert len(snap.token_data) == 1
    td = snap.token_data[0]
    assert td.midpoint == 0.70
    assert td.spread is None
    assert td.book is None
    assert len(snap.fetch_errors) == 2  # spread + book


def test_collector_events_failure_non_blocking(no_version_check_settings: SkillSettings) -> None:
    """events_list 失败不应阻塞整体流程"""
    collector = MarketCollector(settings=no_version_check_settings)

    async def fake_execute(action: str, params: dict[str, Any] | None = None, context: dict[str, Any] | None = None) -> dict[str, Any]:
        if action == "markets_search":
            return _make_ok_result({"markets": []})
        if action == "events_list":
            raise RuntimeError("network down")
        return _make_fail_result("unexpected")

    collector._runner.execute = fake_execute  # type: ignore[method-assign]
    snap = asyncio.run(collector.collect("query", market_limit=1))
    # events 失败，但整体 ok
    assert snap.query == "query"
    assert "events_list" in snap.fetch_errors[0]


def test_collector_actions_called_count(no_version_check_settings: SkillSettings) -> None:
    """actions_called 应等于 1(search) + 4*token_count + 1(events)"""
    collector = MarketCollector(settings=no_version_check_settings)

    async def fake_execute(action: str, params: dict[str, Any] | None = None, context: dict[str, Any] | None = None) -> dict[str, Any]:
        if action == "markets_search":
            return _make_ok_result({
                "markets": [{"conditionId": "m1", "question": "Q?", "clobTokenIds": ["t1", "t2"]}]
            })
        if action in ("clob_midpoint", "clob_spread", "clob_book", "clob_price_history"):
            return _make_ok_result({})
        if action == "events_list":
            return _make_ok_result({"events": []})
        return _make_fail_result("unexpected")

    collector._runner.execute = fake_execute  # type: ignore[method-assign]
    snap = asyncio.run(collector.collect("q"))
    # 1(search) + 2*4(tokens) + 1(events) = 10
    assert snap.actions_called == 10


# ---------------------------------------------------------------------------
# SkillSettings Claude 字段测试
# ---------------------------------------------------------------------------


def test_settings_claude_defaults() -> None:
    s = SkillSettings()
    assert s.anthropic_api_key == ""
    assert s.claude_timeout_seconds == 60
    assert s.claude_max_tokens == 4096


def test_settings_claude_from_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test")
    monkeypatch.setenv("OPENCLAW_CLAUDE_TIMEOUT", "30")
    monkeypatch.setenv("OPENCLAW_CLAUDE_MAX_TOKENS", "2048")
    s = SkillSettings.from_env()
    assert s.anthropic_api_key == "sk-ant-test"
    assert s.claude_timeout_seconds == 30
    assert s.claude_max_tokens == 2048


# ---------------------------------------------------------------------------
# ClaudeClient 测试
# ---------------------------------------------------------------------------

from openclaw_polymarket_skill.claude_client import ClaudeClient, _parse_claude_response


def test_parse_claude_response_valid_json() -> None:
    """正常 JSON 响应解析"""
    payload = json.dumps({
        "structured": {"overall_sentiment": "bullish", "liquidity_score": 0.8},
        "report_markdown": "# 报告\n内容",
    })
    structured, report = _parse_claude_response(payload)
    assert structured["overall_sentiment"] == "bullish"
    assert report == "# 报告\n内容"


def test_parse_claude_response_embedded_json() -> None:
    """响应文本中嵌入 JSON 块"""
    payload = 'Here is my analysis:\n{"structured": {"liquidity_score": 0.5}, "report_markdown": "summary"}\nEnd.'
    structured, report = _parse_claude_response(payload)
    assert structured["liquidity_score"] == 0.5
    assert report == "summary"


def test_parse_claude_response_fallback() -> None:
    """无法解析时降级到原始文本"""
    payload = "This is not JSON at all, just prose."
    structured, report = _parse_claude_response(payload)
    assert structured == {}
    assert report == payload


def test_claude_client_no_api_key() -> None:
    """无 API key 时返回 ok=False"""
    settings = SkillSettings(anthropic_api_key="")
    client = ClaudeClient(settings=settings)
    snap = MarketSnapshot(query="test", markets=[{"id": "m1"}])
    result = client.analyze(snap, "分析")
    assert result.ok is False
    assert "ANTHROPIC_API_KEY" in (result.error or "")


def test_claude_client_anthropic_not_installed() -> None:
    """anthropic 包未安装时返回错误"""
    settings = SkillSettings(anthropic_api_key="sk-ant-fake")
    client = ClaudeClient(settings=settings)
    snap = MarketSnapshot(query="test", markets=[])

    import sys
    with patch.dict(sys.modules, {"anthropic": None}):
        result = client.analyze(snap, "分析")

    assert result.ok is False
    assert "anthropic" in (result.error or "").lower()


def test_claude_client_api_success() -> None:
    """正常调用返回 ok=True 和结构化结果"""
    settings = SkillSettings(anthropic_api_key="sk-ant-fake")
    client = ClaudeClient(settings=settings)
    snap = MarketSnapshot(query="btc", markets=[{"conditionId": "m1", "question": "BTC>100k?"}])

    mock_response_text = json.dumps({
        "structured": {
            "market_assessments": [],
            "overall_sentiment": "bullish",
            "liquidity_score": 0.7,
            "key_risks": [],
            "opportunities": [],
            "data_quality": "good",
        },
        "report_markdown": "# 报告",
    })

    mock_content = MagicMock()
    mock_content.text = mock_response_text
    mock_usage = MagicMock()
    mock_usage.input_tokens = 100
    mock_usage.output_tokens = 200
    mock_response = MagicMock()
    mock_response.content = [mock_content]
    mock_response.usage = mock_usage

    mock_messages = MagicMock()
    mock_messages.create.return_value = mock_response
    mock_anthropic_instance = MagicMock()
    mock_anthropic_instance.messages = mock_messages
    mock_anthropic_class = MagicMock(return_value=mock_anthropic_instance)

    mock_module = MagicMock()
    mock_module.Anthropic = mock_anthropic_class

    import sys
    with patch.dict(sys.modules, {"anthropic": mock_module}):
        result = client.analyze(snap, "分析流动性")

    assert result.ok is True
    assert result.structured["overall_sentiment"] == "bullish"
    assert result.report_markdown == "# 报告"
    assert result.meta["input_tokens"] == 100
    assert result.meta["output_tokens"] == 200


def test_claude_client_api_exception() -> None:
    """API 调用抛异常时返回 ok=False"""
    settings = SkillSettings(anthropic_api_key="sk-ant-fake")
    client = ClaudeClient(settings=settings)
    snap = MarketSnapshot(query="btc", markets=[])

    mock_anthropic_instance = MagicMock()
    mock_anthropic_instance.messages.create.side_effect = RuntimeError("connection refused")
    mock_anthropic_class = MagicMock(return_value=mock_anthropic_instance)
    mock_module = MagicMock()
    mock_module.Anthropic = mock_anthropic_class

    import sys
    with patch.dict(sys.modules, {"anthropic": mock_module}):
        result = client.analyze(snap, "分析")

    assert result.ok is False
    assert "connection refused" in (result.error or "")


# ---------------------------------------------------------------------------
# ReportBuilder 测试
# ---------------------------------------------------------------------------

from openclaw_polymarket_skill.report_builder import build_output


def _make_success_result(query: str = "btc") -> AnalysisResult:
    return AnalysisResult(
        ok=True,
        query=query,
        markets_analyzed=2,
        structured={
            "market_assessments": [
                {
                    "market_id": "0xabc",
                    "question": "BTC > 100k?",
                    "yes_midpoint": 0.65,
                    "spread_bps": 40,
                    "liquidity_quality": "high",
                    "analyst_view": "流动性充足",
                    "notable_signals": ["大量做市商挂单"],
                }
            ],
            "overall_sentiment": "bullish",
            "liquidity_score": 0.8,
            "key_risks": ["监管风险"],
            "opportunities": ["套利机会"],
            "data_quality": "good",
        },
        report_markdown="# 分析报告\n内容摘要",
        meta={"duration_ms": 3000, "model": "claude-opus-4-6", "actions_called": 10},
    )


def test_build_output_json() -> None:
    result = _make_success_result()
    output = build_output(result, fmt="json")
    parsed = json.loads(output)
    assert parsed["ok"] is True
    assert parsed["query"] == "btc"
    assert parsed["markets_analyzed"] == 2


def test_build_output_markdown() -> None:
    result = _make_success_result()
    output = build_output(result, fmt="markdown")
    assert output == "# 分析报告\n内容摘要"


def test_build_output_both_contains_separator() -> None:
    result = _make_success_result()
    output = build_output(result, fmt="both")
    assert "---" in output
    assert "# 分析报告" in output
    assert '"ok": true' in output


def test_build_output_fallback_markdown_no_report() -> None:
    """report_markdown 为空时，应生成 fallback 报告"""
    result = AnalysisResult(
        ok=True,
        query="eth",
        markets_analyzed=1,
        structured={"overall_sentiment": "neutral", "liquidity_score": 0.5, "key_risks": [], "opportunities": [], "data_quality": "partial"},
        report_markdown="",
        meta={"duration_ms": 1000, "model": "claude-opus-4-6", "actions_called": 5},
    )
    output = build_output(result, fmt="markdown")
    assert "eth" in output
    assert "neutral" in output


def test_build_output_error_result() -> None:
    result = AnalysisResult(ok=False, query="test", markets_analyzed=0, error="API 失败")
    output = build_output(result, fmt="json")
    parsed = json.loads(output)
    assert parsed["ok"] is False
    assert parsed["error"] == "API 失败"


# ---------------------------------------------------------------------------
# CLI analyze 子命令测试
# ---------------------------------------------------------------------------

import subprocess
import sys as _sys


def test_cli_analyze_no_api_key(monkeypatch: pytest.MonkeyPatch, tmp_path: Any) -> None:
    """未设置 ANTHROPIC_API_KEY 时退出码应为 2"""
    env = {k: v for k, v in __import__("os").environ.items() if k != "ANTHROPIC_API_KEY"}
    result = subprocess.run(
        [_sys.executable, "-m", "openclaw_polymarket_skill.cli", "analyze",
         "--query", "test", "--analysis-prompt", "test"],
        capture_output=True,
        text=True,
        env=env,
        cwd="/Users/chenge/Desktop/perduction-market/claw-polymarket2.0/claw-polymarket",
    )
    assert result.returncode == 2
    output = json.loads(result.stdout)
    assert output["ok"] is False
    assert "ANTHROPIC_API_KEY" in output["error"]
