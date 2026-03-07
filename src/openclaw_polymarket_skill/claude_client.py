from __future__ import annotations

import json
import re
import time
from typing import Any

from .analyze_models import AnalysisResult, MarketSnapshot
from .settings import SkillSettings

_SYSTEM_PROMPT = """你是一位专业的预测市场分析师，精通 Polymarket 等预测市场的做市机制、流动性分析和概率评估。

请根据用户提供的市场数据和分析任务，输出**纯 JSON**，不包含任何 Markdown 代码块标记或额外说明文字。

输出结构如下：
{
  "structured": {
    "market_assessments": [
      {
        "market_id": "...",
        "question": "...",
        "yes_midpoint": 0.0,
        "spread_bps": 0,
        "liquidity_quality": "high|medium|low",
        "analyst_view": "...",
        "notable_signals": ["..."]
      }
    ],
    "overall_sentiment": "bullish|bearish|neutral|uncertain",
    "liquidity_score": 0.0,
    "key_risks": ["..."],
    "opportunities": ["..."],
    "data_quality": "good|partial|poor"
  },
  "report_markdown": "# 市场分析报告\\n..."
}

要求：
1. market_assessments 必须对每个 market 都有一条记录
2. liquidity_score 范围 0~1，越高代表流动性越好
3. report_markdown 必须包含清晰的 Markdown 格式报告，包括摘要、各市场分析和风险提示
"""


class ClaudeClient:
    """Claude API 封装，支持结构化响应解析和降级策略"""

    def __init__(self, settings: SkillSettings | None = None) -> None:
        self._settings = settings or SkillSettings.from_env()

    def analyze(self, snapshot: MarketSnapshot, analysis_prompt: str) -> AnalysisResult:
        """调用 Claude API 进行市场分析，返回 AnalysisResult"""
        if not self._settings.anthropic_api_key:
            return AnalysisResult(
                ok=False,
                query=snapshot.query,
                markets_analyzed=len(snapshot.markets),
                error="ANTHROPIC_API_KEY 未配置，无法调用 Claude API",
            )

        try:
            import anthropic
        except ImportError:
            return AnalysisResult(
                ok=False,
                query=snapshot.query,
                markets_analyzed=len(snapshot.markets),
                error="anthropic 包未安装，请运行: pip install anthropic",
            )

        market_data_text = json.dumps(snapshot.to_summary_dict(), ensure_ascii=False, indent=2)
        user_message = f"## 分析任务\n{analysis_prompt}\n\n## 市场数据\n{market_data_text}"

        start_ms = int(time.time() * 1000)
        model = "claude-opus-4-6"
        input_tokens = 0
        output_tokens = 0

        try:
            client = anthropic.Anthropic(
                api_key=self._settings.anthropic_api_key,
            )
            response = client.messages.create(
                model=model,
                max_tokens=self._settings.claude_max_tokens,
                system=_SYSTEM_PROMPT,
                messages=[{"role": "user", "content": user_message}],
                timeout=self._settings.claude_timeout_seconds,
            )
            raw_text = response.content[0].text if response.content else ""
            input_tokens = response.usage.input_tokens if response.usage else 0
            output_tokens = response.usage.output_tokens if response.usage else 0
        except Exception as exc:  # noqa: BLE001
            duration_ms = int(time.time() * 1000) - start_ms
            return AnalysisResult(
                ok=False,
                query=snapshot.query,
                markets_analyzed=len(snapshot.markets),
                error=f"Claude API 调用失败: {exc}",
                meta={
                    "duration_ms": duration_ms,
                    "model": model,
                    "input_tokens": 0,
                    "output_tokens": 0,
                    "actions_called": snapshot.actions_called,
                    "fetch_errors_count": len(snapshot.fetch_errors),
                },
            )

        duration_ms = int(time.time() * 1000) - start_ms
        structured, report_markdown = _parse_claude_response(raw_text)

        return AnalysisResult(
            ok=True,
            query=snapshot.query,
            markets_analyzed=len(snapshot.markets),
            structured=structured,
            report_markdown=report_markdown,
            raw_market_data=snapshot.markets,
            meta={
                "duration_ms": duration_ms,
                "model": model,
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "actions_called": snapshot.actions_called,
                "fetch_errors_count": len(snapshot.fetch_errors),
            },
        )


def _parse_claude_response(text: str) -> tuple[dict[str, Any], str]:
    """解析 Claude 输出，返回 (structured, report_markdown)。失败时降级。"""
    # 尝试直接解析整个文本
    text = text.strip()
    try:
        parsed = json.loads(text)
        if isinstance(parsed, dict):
            return parsed.get("structured", {}), parsed.get("report_markdown", text)
    except json.JSONDecodeError:
        pass

    # 尝试提取第一个 {...} 块
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if match:
        try:
            parsed = json.loads(match.group())
            if isinstance(parsed, dict):
                return parsed.get("structured", {}), parsed.get("report_markdown", text)
        except json.JSONDecodeError:
            pass

    # 完全降级：structured 为空，报告为原始文本
    return {}, text
