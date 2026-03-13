# 开发计划：地缘政经驱动的多资产预测分析引擎 v1.0.0

> **⚠️ 此文档已被 `geo-analysis-implementation.md` 取代（2026-03-14）**
>
> 原计划采用 ~1550 行 Python + MCP Server 方案，实际落地改用轻量方案：
> - SKILL.md 注入分析框架（替代 Python 硬编码分类器/信号提取器）
> - findata-tools TS 插件扩展（替代独立 Python 包 + MCP Server）
> - geo_briefing 复合工具（替代 Python 编排器）
>
> 全部已完成，总计 ~408 行 TypeScript，减少 75% 代码量，零新依赖。
> 详见: [`docs/geo-analysis-implementation.md`](geo-analysis-implementation.md)

> 基于 `TRADING_STRATEGY.md` 方法论，将现有 OpenClaw Polymarket Skill (v0.3.1) 升级为完整的地缘政经多资产预测分析系统。

---

## 一、项目概述

### 1.1 当前状态 (v0.3.1)

现有系统是一个 Polymarket CLI 的 Python 封装，提供 21 个原子 action + 基础 AI 分析功能：

```
用户输入关键词 → markets_search → 并行采集 token 数据 → 简单 Claude 分析 → 输出报告
```

**核心局限**：
- System Prompt 仅定义为"预测市场分析师"，缺乏地缘政经分析框架
- 信号解读维度单一（仅 midpoint + spread → 流动性评估）
- 无事件分类和影响链推导能力
- 无多情景构建和价格区间估算
- 输出格式简单（market_assessments 列表），不支持信号仪表盘

### 1.2 目标状态 (v1.0.0)

实现 TRADING_STRATEGY.md 定义的四阶段分析管线：

```
Stage 1: 事件感知与结构化
    ↓ 结构化事件（类型 + 紧急度 + 受影响资产）
Stage 2: 预测市场信号提取（三重角色）
    ├─ 群体智慧：midpoint 概率 + 信号可靠性
    ├─ 领先指标：概率变动速度 + 时间差
    └─ 情绪温度计：spread/book/volume → 情绪矩阵
    ↓ 三角色信号数据包
Stage 3: 综合分析与预测（五层递进）
    ├─ 事件定性评估
    ├─ 概率锚定
    ├─ 影响链推导
    ├─ 多情景构建（乐观/中性/悲观）
    └─ 价格区间估算
    ↓
输出: 结构化 JSON + Markdown 报告 + 信号仪表盘
```

### 1.3 核心升级对照表

| 维度 | v0.3.1 现状 | v1.0.0 目标 |
|------|------------|------------|
| **分析范式** | 单一市场数据 → 简单评估 | 事件检测 → 概率锚定 → 影响链 → 情景推演 → 价格预测 |
| **System Prompt** | 通用预测市场分析师（42行） | 地缘政经分析师 + 五层递进框架（~200行） |
| **信号解读** | midpoint + spread → 流动性评估 | 三重角色（群体智慧/领先指标/情绪温度计） |
| **输出格式** | `market_assessments` 列表 | 结构化 JSON（事件评估/信号/影响链/情景/仪表盘） |
| **接入方式** | CLI `analyze` 命令 | CLI + MCP Server + stdio bridge |
| **覆盖资产** | 仅 Polymarket 盘口 | 加密/美股/大宗/外汇（按事件类型动态选择） |

---

## 二、系统架构设计

### 2.1 整体架构

```
┌─────────────────────────────────────────────────────────────────────┐
│                        接入层（Transport）                           │
│  ┌──────────┐  ┌──────────────┐  ┌──────────────┐  ┌───────────┐  │
│  │ CLI 命令  │  │ stdio bridge │  │  MCP Server  │  │ HTTP API  │  │
│  │geo-analyze│  │ (OpenClaw)   │  │(Claude/IDE)  │  │ (未来扩展) │  │
│  └─────┬────┘  └──────┬───────┘  └──────┬───────┘  └─────┬─────┘  │
└────────┼──────────────┼─────────────────┼────────────────┼─────────┘
         │              │                 │                │
         ▼              ▼                 ▼                ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    编排层（GeoPipeline）                              │
│                                                                     │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────────────┐  │
│  │ EventRouter  │───▶│SignalCollector│───▶│  GeoAnalysisEngine   │  │
│  │ (事件路由)    │    │ (信号采集)    │    │  (分析引擎)           │  │
│  └──────┬───────┘    └──────┬───────┘    └──────────┬───────────┘  │
│         │                   │                       │               │
└─────────┼───────────────────┼───────────────────────┼───────────────┘
          │                   │                       │
          ▼                   ▼                       ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    能力层（Capabilities）                             │
│                                                                     │
│  ┌───────────────┐  ┌────────────────┐  ┌────────────────────────┐ │
│  │EventClassifier│  │MarketCollector │  │   GeoClaudeClient      │ │
│  │ 事件分类器     │  │ (现有,增强)    │  │   地缘分析Claude客户端  │ │
│  │               │  │               │  │                        │ │
│  │·事件类型识别   │  │·markets_search│  │·五层递进System Prompt   │ │
│  │·影响链映射    │  │·token数据采集  │  │·结构化JSON输出Schema   │ │
│  │·紧急度评分    │  │·三重角色提取   │  │·三级降级解析策略       │ │
│  └───────────────┘  └────────────────┘  └────────────────────────┘ │
│                                                                     │
│  ┌───────────────┐  ┌────────────────┐  ┌────────────────────────┐ │
│  │SignalExtractor│  │GeoReportBuilder│  │   现有基础设施          │ │
│  │ 三重角色提取器 │  │ 报告构建器     │  │   (runner/executor/    │ │
│  │               │  │               │  │    security/validators) │ │
│  │·群体智慧信号  │  │·JSON格式化    │  │                        │ │
│  │·领先指标信号  │  │·Markdown报告  │  │                        │ │
│  │·情绪温度计    │  │·信号仪表盘    │  │                        │ │
│  └───────────────┘  └────────────────┘  └────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────┘
          │                   │
          ▼                   ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    外部依赖层                                        │
│  ┌──────────────────┐  ┌──────────────────┐                        │
│  │ polymarket-cli   │  │  Anthropic API   │                        │
│  │ (Rust v0.1.4)    │  │  (Claude Opus)   │                        │
│  └──────────────────┘  └──────────────────┘                        │
└─────────────────────────────────────────────────────────────────────┘
```

### 2.2 新增模块清单

```
src/openclaw_polymarket_skill/
├── geo_models.py           # 地缘分析数据模型（事件/影响链/情景/仪表盘）
├── event_classifier.py     # 事件分类器 + 影响映射矩阵
├── signal_extractor.py     # 三重角色信号提取器
├── geo_claude_client.py    # 地缘分析专用 Claude 客户端
├── geo_prompts.py          # System Prompt + 分析框架指令模板
├── geo_pipeline.py         # 四阶段分析管线编排器
├── geo_report_builder.py   # 地缘分析报告构建器
├── mcp_server.py           # MCP Server 实现
│
├── # 现有文件（需修改）
├── cli.py                  # 新增 geo-analyze + mcp-serve 子命令
├── openclaw_bridge.py      # 新增 geo_analyze method
├── settings.py             # 新增地缘分析相关配置项
└── market_collector.py     # 增强：支持 data_trades 采集
```

### 2.3 数据流详解

```
输入                                    Stage 1                     Stage 2
┌──────────────┐               ┌─────────────────────┐    ┌────────────────────────┐
│ event_text:  │               │  EventClassifier     │    │  MarketCollector        │
│ "美国宣布对   │──────────────▶│                     │    │  + SignalExtractor      │
│  伊朗全面    │               │ ① 事件类型识别       │    │                        │
│  金融制裁"   │               │    → 地缘冲突.制裁升级│    │ ① markets_search       │
│              │               │ ② 紧急度评分         │    │ ② 并行采集 token 数据   │
│ search_query:│               │    → CRITICAL        │    │ ③ 三重角色信号提取      │
│ "Iran        │               │ ③ 受影响资产映射      │    │    ├ 群体智慧信号       │
│  sanctions"  │               │    → 原油↑ 黄金↑     │    │    ├ 领先指标信号       │
│              │               │      股指↓           │    │    └ 情绪温度计         │
└──────────────┘               │ ④ 搜索关键词生成      │    │ ④ 信号可靠性评估       │
                               │    → ["Iran          │    │                        │
                               │     sanctions",...]  │    └────────────┬───────────┘
                               └──────────┬──────────┘                 │
                                          │                            │
                                          ▼                            ▼
                              Stage 3                        输出
                    ┌──────────────────────────┐    ┌────────────────────────┐
                    │  GeoClaudeClient          │    │  GeoReportBuilder      │
                    │  (五层递进分析)             │    │                        │
                    │                          │    │ ① JSON 结构化输出       │
                    │ ① 事件定性评估             │───▶│    event_assessment    │
                    │ ② 预测市场信号三维解读      │    │    prediction_signals  │
                    │ ③ 影响链推导               │    │    asset_impact_map    │
                    │ ④ 多情景构建               │    │    scenarios           │
                    │ ⑤ 综合信号评分             │    │    signal_dashboard    │
                    │ ⑥ 风险与不确定因素         │    │ ② Markdown 分析报告    │
                    │                          │    │ ③ 信号仪表盘可视化     │
                    └──────────────────────────┘    └────────────────────────┘
```

---

## 三、分阶段开发计划

### Stage 1: 数据模型与事件分类引擎

**Goal**: 建立事件分类体系和新的数据模型，作为整个分析管线的基础

**Success Criteria**:
- 7 类事件类型枚举 + 影响映射矩阵可用
- 新数据模型覆盖 TRADING_STRATEGY.md 第五/六章所有输出字段
- 100% 单元测试通过

**Tests**:
- `test_geo_models.py`: 所有 dataclass 可实例化、序列化、反序列化
- 事件分类枚举完整性测试
- 影响映射矩阵查询测试（给定事件类型 → 返回受影响资产列表 + 方向 + 强度）

**详细设计**:

#### geo_models.py 核心数据模型

```python
# 事件类型枚举
class EventType(Enum):
    GEOPOLITICAL_CONFLICT = "地缘冲突"       # 军事行动、制裁升级、领土争端
    CENTRAL_BANK_POLICY = "央行政策"          # 利率决议、QE/QT、前瞻指引
    REGULATORY_POLICY = "监管政策"            # 加密监管、金融监管、反垄断
    ELECTION_REGIME = "选举与政权更迭"         # 大选、弹劾、内阁更换
    TRADE_TARIFF = "贸易与关税"               # 关税调整、贸易协定、制裁
    ECONOMIC_DATA_SHOCK = "经济数据冲击"       # CPI超预期、就业异常
    BLACK_SWAN = "黑天鹅"                     # 疫情、自然灾害、金融机构爆雷

class EventUrgency(Enum):
    CRITICAL = "CRITICAL"       # 概率变化 > 15% / 24h内需反应
    SIGNIFICANT = "SIGNIFICANT" # 概率变化 5%-15% / 1-7天窗口
    MARGINAL = "MARGINAL"       # 概率变化 < 5% / > 7天可跟踪

class ImpactDirection(Enum):
    BULLISH = "BULLISH"
    BEARISH = "BEARISH"
    NEUTRAL = "NEUTRAL"

class ImpactStrength(Enum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"

class TimeLag(Enum):
    IMMEDIATE = "IMMEDIATE"     # 分钟级
    HOURS = "HOURS"             # 小时级
    DAYS = "DAYS"               # 天级
    WEEKS = "WEEKS"             # 周级

# 核心数据结构
@dataclass
class EventAssessment:
    summary: str
    event_type: EventType
    sub_type: str
    novelty: str          # NEW | DEVELOPMENT | ESCALATION | DE-ESCALATION
    urgency: EventUrgency
    market_expectation: str  # UNEXPECTED | PARTIALLY_EXPECTED | FULLY_PRICED
    timestamp: str

@dataclass
class ImpactChain:
    path: str                    # 传导路径描述
    affected_asset: str          # 受影响资产
    direction: ImpactDirection
    impact_strength: ImpactStrength
    time_lag: TimeLag
    order: int                   # 1=一阶影响, 2=二阶影响

@dataclass
class Scenario:
    name: str                    # bullish / neutral / bearish
    trigger: str
    probability: float           # 0-1, 三情景之和 = 1.0
    price_target: str
    rationale: str

@dataclass
class SignalDashboard:
    direction_score: float       # -1.0 到 +1.0
    confidence: str              # HIGH / MEDIUM / LOW
    time_horizon: str            # IMMEDIATE / SHORT_TERM / MEDIUM_TERM
    volatility_expectation: str  # ELEVATED / NORMAL / COMPRESSED
    overall_recommendation: str

@dataclass
class PredictionMarketSignal:
    market_question: str
    midpoint: float
    trend_24h: str
    signal_reliability: str      # HIGH / MEDIUM / LOW
    crowd_wisdom_reading: str
    leading_indicator_reading: str
    sentiment_gauge_reading: str

@dataclass
class GeoAnalysisResult:
    ok: bool
    event_assessment: EventAssessment | None
    prediction_market_signals: list[PredictionMarketSignal]
    asset_impact_map: list[ImpactChain]
    scenarios: dict[str, Scenario]  # bullish/neutral/bearish
    signal_dashboard: SignalDashboard | None
    risk_factors: list[str]
    reassessment_trigger: str
    report_markdown: str
    raw_market_data: list[dict]
    error: str | None
    meta: dict
```

#### event_classifier.py 影响映射矩阵

```python
# 映射规则示例
IMPACT_MATRIX = {
    EventType.GEOPOLITICAL_CONFLICT: [
        ImpactChain(path="避险需求上升", affected_asset="Gold (XAU)",
                    direction=BULLISH, impact_strength=HIGH, time_lag=HOURS, order=1),
        ImpactChain(path="能源供应担忧", affected_asset="WTI Crude Oil",
                    direction=BULLISH, impact_strength=HIGH, time_lag=HOURS, order=1),
        ImpactChain(path="风险偏好下降", affected_asset="S&P 500",
                    direction=BEARISH, impact_strength=MEDIUM, time_lag=HOURS, order=1),
        ImpactChain(path="风险偏好下降", affected_asset="BTC",
                    direction=BEARISH, impact_strength=MEDIUM, time_lag=HOURS, order=1),
    ],
    EventType.CENTRAL_BANK_POLICY: [...],
    # ... 7 类完整映射
}
```

**Status**: Not Started

---

### Stage 2: 升级分析引擎 System Prompt + GeoClaudeClient

**Goal**: 重写 Claude 分析引擎，实现五层递进分析框架

**Success Criteria**:
- 新 System Prompt 包含六步分析指令
- GeoClaudeClient 输出严格符合 TRADING_STRATEGY.md 第六章 JSON Schema
- 支持新旧两种分析模式（向后兼容现有 `analyze` 命令）

**Tests**:
- `test_geo_claude_client.py`: 模拟 Claude 响应 → 正确解析为 GeoAnalysisResult
- 降级策略测试（JSON 解析失败时的 fallback）
- System Prompt 内容完整性断言

**详细设计**:

#### geo_prompts.py System Prompt 核心结构

```python
GEO_SYSTEM_PROMPT = """
你是一位专精于地缘政治经济学的资产分析师，具备以下能力：
1. 深刻理解地缘政治事件对全球金融市场的传导机制
2. 精通预测市场（Polymarket）的盘口数据解读——
   将群体下注概率转化为资产价格分析的信号输入
3. 能够构建多情景分析框架，给出概率加权的价格预测

你的分析原则：
- 预测市场盘口是群体智慧的浓缩，但不是真理——需要独立验证
- 所有预测必须明确置信度和有效时间窗口
- 区分一阶影响（直接且快速）和二阶影响（间接且滞后）
- 永远考虑"市场已定价多少"——避免对已知信息做冗余分析

按照以下六步框架分析：
1. 事件定性评估 [...]
2. 预测市场信号三维解读 [...]
3. 影响链推导 [...]
4. 多情景构建 [...]
5. 综合信号评分 [...]
6. 风险与不确定因素 [...]

输出严格 JSON 格式：{完整 Schema}
"""
```

#### geo_claude_client.py 关键接口

```python
class GeoClaudeClient:
    def __init__(self, settings: SkillSettings) -> None: ...

    def analyze(
        self,
        event_text: str,
        event_assessment: EventAssessment,
        signal_package: SignalPackage,
        impact_chains: list[ImpactChain],
    ) -> GeoAnalysisResult:
        """
        将事件信息 + 信号数据 + 影响链映射组装为 prompt,
        调用 Claude API, 解析结构化输出
        """
```

**Status**: Not Started

---

### Stage 3: 三重角色信号提取器

**Goal**: 实现 Polymarket 盘口数据的三重角色解读

**Success Criteria**:
- 群体智慧：midpoint + 可靠性评分（交易量 × 存续时间）
- 领先指标：概率变动速度 + 方向持续性 + 基准水平判定
- 情绪温度计：spread × book平衡度 × 交易量 → 4种情绪状态
- 输出 SignalPackage 供 Claude 使用

**Tests**:
- `test_signal_extractor.py`: 覆盖 4 种情绪矩阵状态、概率变动速度计算、可靠性评估

**详细设计**:

#### signal_extractor.py 核心逻辑

```python
@dataclass
class CrowdWisdomSignal:
    midpoint: float
    signal_reliability: str  # HIGH / MEDIUM / LOW
    volume_24h: float
    market_age_days: int
    reading: str             # 自然语言解读

@dataclass
class LeadingIndicatorSignal:
    price_change_1h: float
    price_change_24h: float
    change_velocity: str     # FAST / MODERATE / SLOW
    direction_persistence: int  # 连续同向时段数
    base_level: str          # LOW_PROB / MID_PROB / HIGH_PROB
    reading: str

class SentimentState(Enum):
    STABLE_CONSENSUS = "稳定共识"       # spread窄 + book平衡 + volume高
    DIRECTIONAL_CONSENSUS = "方向性共识" # spread窄 + book不平衡 + volume高
    UNCERTAIN_ANXIETY = "不确定焦虑"     # spread宽 + book不平衡 + volume低
    FIERCE_DIVERGENCE = "激烈分歧"       # spread宽 + book平衡 + volume高

@dataclass
class SentimentGaugeSignal:
    spread_bps: float
    book_imbalance: float    # -1(偏sell) 到 +1(偏buy)
    volume_level: str        # HIGH / MEDIUM / LOW
    sentiment_state: SentimentState
    reading: str

@dataclass
class SignalPackage:
    """一个预测市场盘口的三重角色信号数据包"""
    market_question: str
    crowd_wisdom: CrowdWisdomSignal
    leading_indicator: LeadingIndicatorSignal
    sentiment_gauge: SentimentGaugeSignal

class SignalExtractor:
    def extract(self, token_data: TokenData, market_info: dict) -> SignalPackage:
        """从采集到的 token 数据中提取三重角色信号"""

    def _assess_crowd_wisdom(self, td: TokenData, market: dict) -> CrowdWisdomSignal: ...
    def _assess_leading_indicator(self, td: TokenData) -> LeadingIndicatorSignal: ...
    def _assess_sentiment_gauge(self, td: TokenData) -> SentimentGaugeSignal: ...
    def _classify_sentiment_state(self, spread, imbalance, volume) -> SentimentState: ...
```

**情绪状态矩阵判定逻辑**:

| Spread | Book 平衡度 | 交易量 | → 情绪状态 |
|--------|------------|--------|-----------|
| 窄 (<50bps) | 平衡 (|imbalance|<0.3) | 高 | 稳定共识 |
| 窄 (<50bps) | 不平衡 (|imbalance|≥0.3) | 高 | 方向性共识 |
| 宽 (≥200bps) | 不平衡 | 低 | 不确定焦虑 |
| 宽 (≥200bps) | 平衡 | 高 | 激烈分歧 |

**Status**: Not Started

---

### Stage 4: 地缘分析管线编排 + CLI/Bridge 入口

**Goal**: 串联 Stage 1-3，实现完整管线并暴露为 CLI 命令和 bridge method

**Success Criteria**:
- `geo-analyze` CLI 命令可用
- 完整管线：事件分类 → 信号提取 → Claude 深度分析 → 格式化输出
- bridge 协议支持 `geo_analyze` method

**Tests**:
- `test_geo_pipeline.py`: 端到端管线测试（mock 外部调用）
- CLI 集成测试
- bridge method 路由测试

**详细设计**:

#### geo_pipeline.py 管线编排

```python
class GeoPipeline:
    """四阶段分析管线编排器"""

    def __init__(self, settings: SkillSettings) -> None:
        self._classifier = EventClassifier()
        self._collector = MarketCollector(settings)
        self._extractor = SignalExtractor()
        self._claude = GeoClaudeClient(settings)
        self._report = GeoReportBuilder()

    async def analyze(
        self,
        event_text: str,
        search_queries: list[str] | None = None,
        market_limit: int = 5,
    ) -> GeoAnalysisResult:
        """
        完整分析流程：
        1. 事件分类 + 影响链映射
        2. 市场数据采集 + 三重角色信号提取
        3. Claude 五层递进分析
        4. 报告构建
        """

        # Stage 1: 事件分类
        event = self._classifier.classify(event_text)
        impact_chains = self._classifier.map_impacts(event.event_type)
        queries = search_queries or self._classifier.generate_search_queries(event)

        # Stage 2: 信号采集
        all_signals: list[SignalPackage] = []
        for query in queries:
            snapshot = await self._collector.collect(query, market_limit)
            for market in snapshot.markets:
                for td in snapshot.token_data:
                    if td.token_id in (market.get("clobTokenIds") or []):
                        signal = self._extractor.extract(td, market)
                        all_signals.append(signal)

        # Stage 3: Claude 深度分析
        result = self._claude.analyze(
            event_text=event_text,
            event_assessment=event,
            signal_package=all_signals,
            impact_chains=impact_chains,
        )

        return result
```

#### CLI 新增子命令

```python
# cli.py 新增
geo_analyze = sub.add_parser("geo-analyze",
    help="地缘政经事件驱动的多资产预测分析")
geo_analyze.add_argument("--event", required=True,
    help="事件描述文本（如：'美国宣布对伊朗全面金融制裁'）")
geo_analyze.add_argument("--queries", nargs="*",
    help="预测市场搜索关键词（可选，不提供则自动生成）")
geo_analyze.add_argument("--market-limit", type=int, default=5)
geo_analyze.add_argument("--output", choices=["json","markdown","both"], default="both")
```

#### Bridge 协议扩展

```json
{
  "id": "req-1",
  "method": "geo_analyze",
  "params": {
    "event_text": "美国宣布对伊朗全面金融制裁",
    "search_queries": ["Iran sanctions", "oil supply"],
    "market_limit": 5
  }
}
```

**Status**: Not Started

---

### Stage 5: MCP Server 封装 + 安装集成

**Goal**: 封装为标准 MCP Server，可被 Claude Desktop / OpenClaw / 任何 MCP 客户端调用

**Success Criteria**:
- MCP Server 提供 3 个 tools
- 支持 `stdio` transport
- `pip install .` 后可通过 `openclaw-polymarket-skill mcp-serve` 启动
- 提供 MCP 配置模板

**Tests**:
- `test_mcp_server.py`: tool 注册/调用/响应格式测试

**详细设计**:

#### MCP Tools 定义

```python
# Tool 1: geo_analyze（完整分析）
{
    "name": "geo_analyze",
    "description": "地缘政经事件驱动的多资产预测分析。输入事件描述，输出结构化预测（含影响链、多情景、信号仪表盘）",
    "inputSchema": {
        "type": "object",
        "properties": {
            "event_text": {
                "type": "string",
                "description": "地缘政经事件描述"
            },
            "search_queries": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Polymarket搜索关键词（可选，不提供则自动生成）"
            },
            "market_limit": {
                "type": "integer",
                "default": 5,
                "description": "每个关键词最多分析的市场数量"
            }
        },
        "required": ["event_text"]
    }
}

# Tool 2: market_signal（轻量信号查询）
{
    "name": "market_signal",
    "description": "查询特定预测市场的三重角色信号（群体智慧/领先指标/情绪温度计）",
    "inputSchema": {
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "市场搜索关键词"},
            "market_limit": {"type": "integer", "default": 3}
        },
        "required": ["query"]
    }
}

# Tool 3: event_classify（事件分类）
{
    "name": "event_classify",
    "description": "对地缘政经事件进行分类，输出事件类型、紧急度、受影响资产映射",
    "inputSchema": {
        "type": "object",
        "properties": {
            "event_text": {"type": "string", "description": "事件描述"}
        },
        "required": ["event_text"]
    }
}
```

#### MCP Server 实现方案

```python
# 使用 mcp 官方 Python SDK
from mcp.server import Server
from mcp.server.stdio import stdio_server

app = Server("openclaw-polymarket-geo")

@app.list_tools()
async def list_tools() -> list[Tool]: ...

@app.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]: ...

async def main():
    async with stdio_server() as (read, write):
        await app.run(read, write, app.create_initialization_options())
```

#### MCP 客户端配置模板

```json
{
  "mcpServers": {
    "openclaw-polymarket-geo": {
      "command": "openclaw-polymarket-skill",
      "args": ["mcp-serve"],
      "env": {
        "ANTHROPIC_API_KEY": "sk-ant-xxx",
        "OPENCLAW_PM_BIN": "polymarket"
      }
    }
  }
}
```

#### pyproject.toml 依赖更新

```toml
dependencies = [
    "anthropic>=0.37.0",
    "mcp>=1.0.0",        # 新增 MCP SDK
]
```

**Status**: Not Started

---

## 四、输出格式规范

### 4.1 完整 JSON 输出 Schema

基于 TRADING_STRATEGY.md 第六章定义：

```json
{
  "event_assessment": {
    "summary": "事件简述",
    "type": "地缘冲突.制裁升级",
    "novelty": "NEW | DEVELOPMENT | ESCALATION | DE-ESCALATION",
    "market_expectation": "UNEXPECTED | PARTIALLY_EXPECTED | FULLY_PRICED",
    "urgency": "CRITICAL | SIGNIFICANT | MARGINAL"
  },
  "prediction_market_signals": {
    "primary_market": {
      "question": "相关预测市场问题",
      "midpoint": 0.68,
      "trend_24h": "+23%",
      "signal_reliability": "HIGH"
    },
    "crowd_wisdom_reading": "市场认为制裁落地概率68%，信号可靠性高（日均交易量$125k）",
    "leading_indicator_reading": "24h内概率跳升23%，传统市场尚未充分反应",
    "sentiment_gauge_reading": "spread收窄至30bps，方向性共识强烈偏YES"
  },
  "asset_impact_map": [
    {
      "asset": "WTI Crude Oil",
      "direction": "BULLISH",
      "impact_strength": "HIGH",
      "transmission_path": "全面金融制裁 → 原油出口受阻 → 全球供应缺口",
      "time_lag": "HOURS"
    }
  ],
  "scenarios": {
    "bullish": {
      "trigger": "制裁正式生效且无豁免条款",
      "probability": 0.55,
      "price_target": "$82-86",
      "rationale": "供应缺口约200万桶/日，历史类似案例价格上涨8-12%"
    },
    "neutral": {
      "trigger": "制裁附带宽泛豁免或延迟执行",
      "probability": 0.30,
      "price_target": "$78-81",
      "rationale": "市场已部分定价，豁免减弱实际供应冲击"
    },
    "bearish": {
      "trigger": "制裁被搁置或外交突破",
      "probability": 0.15,
      "price_target": "$74-77",
      "rationale": "预期落空导致多头平仓，叠加全球需求疲软"
    }
  },
  "signal_dashboard": {
    "direction_score": 0.55,
    "confidence": "MEDIUM",
    "time_horizon": "SHORT_TERM",
    "volatility_expectation": "ELEVATED",
    "overall_recommendation": "原油短期偏多，置信度中等。关键催化剂为制裁生效日。"
  },
  "risk_factors": [
    "预测市场流动性不足可能导致概率信号偏差",
    "OPEC可能增产对冲制裁影响",
    "外交斡旋仍有突破可能"
  ],
  "reassessment_trigger": "制裁正式执行日（3月15日）或出现外交突破消息",
  "report_markdown": "# 完整 Markdown 分析报告\n..."
}
```

### 4.2 Markdown 报告模板

```markdown
# 地缘政经分析报告

## 事件评估
- **事件**: {summary}
- **类型**: {type}
- **新颖度**: {novelty}
- **紧急度**: {urgency}
- **市场预期**: {market_expectation}

## 预测市场信号（三重角色解读）

### 主要盘口
**{market_question}** → midpoint: {midpoint} ({trend_24h})

| 角色 | 信号解读 |
|------|---------|
| 群体智慧 | {crowd_wisdom_reading} |
| 领先指标 | {leading_indicator_reading} |
| 情绪温度计 | {sentiment_gauge_reading} |

## 资产影响链
{每条影响链的 表格/列表 展示}

## 多情景分析
### 乐观情景 (概率: {p}%)
...
### 中性情景 (概率: {p}%)
...
### 悲观情景 (概率: {p}%)
...

## 信号仪表盘
| 指标 | 值 |
|------|-----|
| 方向得分 | {direction_score} |
| 置信度 | {confidence} |
| 时间框架 | {time_horizon} |
| 波动预期 | {volatility_expectation} |
| **综合建议** | **{overall_recommendation}** |

## 风险因素
{风险列表}

---
*再评估触发点: {reassessment_trigger}*
```

---

## 五、依赖关系与版本规划

### 5.1 Stage 依赖关系

```
Stage 1 (数据模型+事件分类) ──┐
                              ├──→ Stage 3 (信号提取) ──┐
Stage 2 (Claude分析引擎) ─────┘                        ├──→ Stage 4 (管线编排) ──→ Stage 5 (MCP)
```

- Stage 1 + Stage 2 **可并行开发**
- Stage 3 依赖 Stage 1 的数据模型
- Stage 4 依赖 Stage 1/2/3 全部完成
- Stage 5 依赖 Stage 4

### 5.2 版本里程碑

| 版本 | 内容 | 新增 Python 代码行数(估) |
|------|------|------------------------|
| v0.4.0 | Stage 1 + 2（数据模型 + 分析引擎） | ~600 |
| v0.5.0 | Stage 3（三重角色信号提取） | ~300 |
| v0.9.0 | Stage 4（完整管线 + CLI + Bridge） | ~400 |
| v1.0.0 | Stage 5（MCP Server + 文档 + 配置模板） | ~250 |

### 5.3 新增依赖

```toml
# pyproject.toml
dependencies = [
    "anthropic>=0.37.0",   # 已有
    "mcp>=1.0.0",          # 新增：MCP Server SDK
]
```

---

## 六、模型选择与 Agent 协调策略

### 6.1 Claude 模型选择

| 使用场景 | 推荐模型 | 理由 |
|----------|---------|------|
| 完整地缘分析（geo_analyze） | `claude-opus-4-6` | 需要深层因果推理、多情景构建、概率校准 |
| 轻量信号查询（market_signal） | `claude-sonnet-4-6` | 仅做信号数据格式化解读，不需要深度推理 |
| 事件分类（event_classify） | `claude-haiku-4-5` | 分类任务相对简单，速度优先 |

### 6.2 多 Agent 协调模式

当本 MCP Server 被 OpenClaw 或其他 Agent 调用时，推荐的编排模式：

```
┌────────────────────────────────────────────────────────┐
│              主 Agent（OpenClaw 核心 / 用户对话）         │
│                                                        │
│  用户: "分析一下伊朗制裁对油价的影响"                     │
│                                                        │
│  ① 调用 event_classify → 快速分类（Haiku，<1s）          │
│  ② 基于分类结果，并行调用:                               │
│     ├─ market_signal("Iran sanctions")                  │
│     ├─ market_signal("oil supply disruption")           │
│     └─ market_signal("OPEC production")                 │
│  ③ 汇总信号，调用 geo_analyze（Opus，10-30s）            │
│  ④ 将报告返回用户                                       │
└────────────────────────────────────────────────────────┘
```

或者一步到位：

```
用户: "分析伊朗制裁对油价的影响"
  → 直接调用 geo_analyze(event_text="美国对伊朗全面金融制裁")
  → 内部自动完成 分类 → 采集 → 提取 → 分析 → 输出
```

### 6.3 Token 消耗估算

| 操作 | 输入 tokens | 输出 tokens | 费用估算(Opus) |
|------|-----------|-----------|---------------|
| geo_analyze（完整分析） | ~8,000 | ~4,000 | ~$0.18 |
| market_signal（信号查询） | ~3,000 | ~1,500 | ~$0.07 |
| event_classify（事件分类） | ~500 | ~300 | ~$0.01 (Haiku) |

---

## 七、测试策略

### 7.1 新增测试文件

```
tests/
├── test_geo_models.py          # 数据模型序列化/反序列化
├── test_event_classifier.py    # 事件分类 + 影响映射
├── test_signal_extractor.py    # 三重角色信号提取
├── test_geo_claude_client.py   # Claude 调用 + 响应解析
├── test_geo_pipeline.py        # 端到端管线（mock 外部依赖）
├── test_mcp_server.py          # MCP tool 注册/调用
```

### 7.2 测试原则

- **所有外部调用必须 mock**：polymarket CLI subprocess + Anthropic API
- **覆盖率要求 ≥ 80%**（延续现有 pytest.ini 配置）
- **边界条件重点覆盖**：
  - 空市场数据时的降级输出
  - Claude API 超时/失败时的 fallback
  - 不可识别事件类型时的默认行为
  - 低流动性市场的信号可靠性降级

---

## 八、安装与使用指南（预览）

### 8.1 安装

```bash
# 克隆仓库
git clone <repo-url>
cd openclaw-polymarket-skill

# 安装（含 MCP 依赖）
pip install -e ".[dev]"

# 确保 polymarket CLI 在 PATH
which polymarket  # 应输出路径

# 配置环境变量
export ANTHROPIC_API_KEY=sk-ant-xxxxx
export OPENCLAW_PM_BIN=polymarket
```

### 8.2 CLI 使用

```bash
# 完整地缘分析
openclaw-polymarket-skill geo-analyze \
  --event "美国宣布对伊朗实施全面金融制裁" \
  --queries "Iran sanctions" "oil supply" \
  --market-limit 5 \
  --output both

# 兼容旧版简单分析
openclaw-polymarket-skill analyze \
  --query "bitcoin ETF" \
  --analysis-prompt "分析BTC ETF审批概率" \
  --output both
```

### 8.3 MCP Server 使用

```bash
# 启动 MCP Server（stdio 模式）
openclaw-polymarket-skill mcp-serve
```

Claude Desktop 配置 (`claude_desktop_config.json`):
```json
{
  "mcpServers": {
    "openclaw-polymarket-geo": {
      "command": "openclaw-polymarket-skill",
      "args": ["mcp-serve"],
      "env": {
        "ANTHROPIC_API_KEY": "sk-ant-xxx",
        "OPENCLAW_PM_BIN": "polymarket"
      }
    }
  }
}
```

### 8.4 OpenClaw Bridge 使用

```bash
# stdio bridge（兼容现有 + 新功能）
openclaw-polymarket-skill serve-stdio
```

请求示例：
```json
{"id":"1","method":"geo_analyze","params":{"event_text":"美国对伊朗全面金融制裁","market_limit":5}}
```

---

## 九、风险与缓解措施

| 风险 | 影响 | 缓解 |
|------|------|------|
| Claude API 输出不稳定 | 结构化 JSON 解析失败 | 三级降级策略（直接解析 → 提取JSON块 → 原始文本） |
| Polymarket 低流动性 | 信号可靠性低 | 可靠性评分降级 + 输出警告标记 |
| 事件分类准确率不足 | 影响链映射错误 | 分类结果附带 confidence，低于阈值时由 Claude 重新判断 |
| MCP SDK 版本兼容性 | 启动失败 | 锁定 mcp>=1.0.0，CI 中测试 |
| Token 消耗过高 | 成本不可控 | 配置 max_tokens 上限 + 按模型分级调用 |
