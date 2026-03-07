from __future__ import annotations

import json
from typing import Any, Literal

from .analyze_models import AnalysisResult

OutputFormat = Literal["json", "markdown", "both"]


def build_output(result: AnalysisResult, fmt: OutputFormat = "both") -> str:
    """将 AnalysisResult 格式化为指定输出格式的字符串"""
    if fmt == "json":
        return _to_json(result)
    if fmt == "markdown":
        return _to_markdown(result)
    # both: JSON 在前，Markdown 在后（用分隔符分开）
    json_part = _to_json(result)
    md_part = result.report_markdown or ""
    return f"{json_part}\n\n---\n\n{md_part}"


def _to_json(result: AnalysisResult) -> str:
    return json.dumps(result.to_dict(), ensure_ascii=False, indent=2)


def _to_markdown(result: AnalysisResult) -> str:
    """若已有 report_markdown 则直接返回；否则按结构化数据生成简易报告"""
    if result.report_markdown:
        return result.report_markdown
    return _generate_fallback_markdown(result)


def _generate_fallback_markdown(result: AnalysisResult) -> str:
    lines: list[str] = []
    lines.append(f"# Polymarket 市场分析报告")
    lines.append(f"\n**查询词**: {result.query}")
    lines.append(f"**分析市场数**: {result.markets_analyzed}")

    if not result.ok:
        lines.append(f"\n**错误**: {result.error}")
        return "\n".join(lines)

    s = result.structured
    if s:
        sentiment = s.get("overall_sentiment", "N/A")
        liquidity = s.get("liquidity_score", "N/A")
        data_quality = s.get("data_quality", "N/A")
        lines.append(f"\n## 总体评估")
        lines.append(f"- **市场情绪**: {sentiment}")
        lines.append(f"- **流动性评分**: {liquidity}")
        lines.append(f"- **数据质量**: {data_quality}")

        key_risks = s.get("key_risks") or []
        if key_risks:
            lines.append(f"\n## 主要风险")
            for risk in key_risks:
                lines.append(f"- {risk}")

        opportunities = s.get("opportunities") or []
        if opportunities:
            lines.append(f"\n## 机会")
            for opp in opportunities:
                lines.append(f"- {opp}")

        assessments = s.get("market_assessments") or []
        if assessments:
            lines.append(f"\n## 各市场分析")
            for a in assessments:
                lines.append(f"\n### {a.get('question', a.get('market_id', '未知'))}")
                lines.append(f"- **中间价**: {a.get('yes_midpoint', 'N/A')}")
                lines.append(f"- **价差(bps)**: {a.get('spread_bps', 'N/A')}")
                lines.append(f"- **流动性**: {a.get('liquidity_quality', 'N/A')}")
                if a.get("analyst_view"):
                    lines.append(f"- **分析**: {a['analyst_view']}")
                signals = a.get("notable_signals") or []
                if signals:
                    lines.append("- **信号**:")
                    for sig in signals:
                        lines.append(f"  - {sig}")

    meta = result.meta
    if meta:
        lines.append(f"\n---")
        lines.append(f"*耗时: {meta.get('duration_ms', 0)}ms | 模型: {meta.get('model', 'N/A')} | 调用动作数: {meta.get('actions_called', 0)}*")

    return "\n".join(lines)
