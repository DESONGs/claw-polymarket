# Geo-Analysis Implementation Plan: Architecture & Landing Strategy

> 基于 `TRADING_STRATEGY.md` 方法论 + 现有 OpenClaw 架构分析，制定最小改动、最大复用的落地方案。
>
> 创建日期: 2026-03-14

---

## 一、现有架构盘点

### 1.1 Agent 结构

| Agent | Model | Role |
|-------|-------|------|
| `main` | `moonshot/kimi-k2.5` | 主 Agent，承担所有分析调度 |
| `lingzhu` | `deepseek/deepseek-chat` | Rokid 智能眼镜桥接 |

- 2026-03-12 从双 Agent（dispatcher + analyst）合并为单 Agent
- 配置文件: `.openclaw/openclaw.json` agents 段

### 1.2 工具注册情况

**findata-tools 插件**（当前生效的原生工具）:

| Category | Tools | API Source |
|----------|-------|-----------|
| Twitter | `twitter_search`, `twitter_user_tweets`, `twitter_user_info` | ai.6551.io |
| News | `news_search`, `news_sources` | ai.6551.io |
| Polymarket | `polymarket_search`, `polymarket_market_detail`, `polymarket_midpoint`, `polymarket_spread`, `polymarket_price_history`, `polymarket_book` | gamma-api / clob.polymarket.com |
| OpenBB | `openbb_stock`, `openbb_company_info`, `openbb_economy` | 127.0.0.1:6900 |
| Composite | `geo_briefing` | 内部并行调用上述全部 API |

插件路径: `.openclaw/workspace/skills/findata-tools/extension/`
注册方式: `api.registerTool()` in `index.ts`

**已废弃的 SKILL.md 体系**: opentwitter, opennews, polymarket, openbb 均已标记 `user-invocable: false`

### 1.3 调度逻辑

```
用户请求 → Gateway(:18789) → main Agent(kimi-k2.5)
  → 模型自主选择工具 → 执行 → 模型综合分析 → 返回
```

无 dispatcher 路由层，模型直接决定调用哪些工具。

### 1.4 上下文管理

- Compaction mode: `safeguard`（保守，保留更多历史）
- skillsSnapshot 缓存: 安装新 skill 后必须手动清除
- Session 隔离: `agent:main:main`（通用），`agent:main:telegram:*`（Telegram）

---

## 二、需求差距分析

对比 `TRADING_STRATEGY.md` 的四阶段分析管线与现有能力:

| TRADING_STRATEGY 需要 | 现有覆盖 | 差距 |
|---|---|---|
| Stage 1: 事件感知（Twitter + News） | `twitter_search` + `news_search` | **无差距** |
| Stage 2: 资产价格数据 | `openbb_stock` (quote/history) | **无差距** |
| Stage 2: 经济日历 | `openbb_economy` (calendar/gdp/cpi) | **无差距** |
| Stage 3: Polymarket 搜索 + midpoint | `polymarket_search` + `polymarket_midpoint` | **无差距** |
| Stage 3: 概率变动趋势 (price_history) | 无 | **需新增 CLOB 端点** |
| Stage 3: 做市商确信度 (spread) | 无 | **需新增 CLOB 端点** |
| Stage 3: 买卖方向压力 (orderbook) | 无 | **需新增 CLOB 端点** |
| Stage 3: 三重角色信号解读框架 | 无 (agent 无此知识) | **需 SKILL.md 注入** |
| Stage 4: 事件分类 + 影响链映射 | 无 (全在 agent 脑子里) | **需 SKILL.md 注入** |
| Stage 4: 五层递进分析框架 | 无 (无 system prompt 指导) | **需 SKILL.md 注入** |
| 编排: 并行数据采集 | 无 (agent 逐个调用，6-8 轮 LLM) | **可选: composite tool** |

---

## 三、落地方案: 三层架构

### 设计原则

- **不建独立 Python 包** — findata-tools 已覆盖数据层
- **不新增 Claude API 调用** — main agent 自身就是 LLM，用 SKILL.md 指导即可
- **不建 MCP Server** — 工具已作为 native tool 注册
- **不硬编码事件分类器** — 影响映射矩阵放在 SKILL.md 让 LLM 直接用，比硬编码更灵活

### 架构图

```
┌────────────────────────────────────────────────────────────┐
│                    main Agent (kimi-k2.5)                   │
│                                                            │
│  System Prompt += geo-analysis SKILL.md                    │
│  (五层递进框架 / 事件分类体系 / 影响映射矩阵 / 输出 Schema)  │
│                                                            │
│  工具调用策略:                                               │
│  A) geo_briefing (一键并行取全部数据) — Step 3 实现         │
│  B) 或逐个调用原子工具 (灵活组合) — Step 1 即可用           │
│  C) 基于 SKILL.md 框架做五层分析                            │
└────────────┬───────────────────────────────────────────────┘
             │
    ┌────────┴─────────────────────────────────────────────┐
    │              findata-tools Plugin (enhanced)          │
    │                                                      │
    │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌────────┐ │
    │  │ Twitter  │ │  News    │ │Polymarket│ │ OpenBB │ │
    │  │ 3 tools  │ │ 2 tools  │ │ 3→6 tools│ │ 3 tools│ │
    │  └──────────┘ └──────────┘ └──────────┘ └────────┘ │
    │                                                      │
    │  ┌──────────────────────────────────────────────────┐│
    │  │ geo_briefing (NEW composite tool)                ││
    │  │ parallel: twitter + news + polymarket + openbb   ││
    │  │ → returns assembled data brief (Step 3)          ││
    │  └──────────────────────────────────────────────────┘│
    └──────────────────────────────────────────────────────┘
```

### 三层改动

| Layer | What | Files | Lines | Status |
|-------|------|-------|-------|--------|
| **Layer 1: Knowledge** | SKILL.md 注入分析框架 | `skills/geo-analysis/SKILL.md` + `_meta.json` | ~150 | DONE ✓ |
| **Layer 2: Data** | 补齐 Polymarket CLOB 端点 | `src/polymarket-tools.ts` | +80 | DONE ✓ |
| **Layer 3: Orchestration** | geo_briefing 复合工具 | 新增 `src/geo-briefing.ts` + 改 `index.ts` | ~170+8 | DONE ✓ |
| | **Total** | | **~408** | **ALL DONE** |

对比 GEO_ANALYSIS_DEV_PLAN 的 ~1550 行 Python + MCP，**减少 75% 代码量**，零新依赖。

---

## 四、实施步骤

### Step 1: SKILL.md + 注册 (DONE ✓ 2026-03-14)

- [x] 创建 `.openclaw/workspace/skills/geo-analysis/SKILL.md`
- [x] 创建 `.openclaw/workspace/skills/geo-analysis/_meta.json`
- [x] 注册到 `.openclaw/workspace/.clawhub/lock.json`
- [x] 清除 agents skillsSnapshot 缓存
- [x] 重启 gateway 验证

**效果**: Agent 立即可用五层分析框架，逐个调用现有工具完成分析。

### Step 2: 补齐 Polymarket CLOB 端点 (DONE ✓ 2026-03-14)

改动文件: `findata-tools/extension/src/polymarket-tools.ts`

新增 3 个 helper 函数 (`getSpread`, `getPriceHistory`, `getBook`) + 3 个工具定义:

| Tool | CLOB Endpoint | Three-Role Usage |
|------|--------------|-----------------|
| `polymarket_spread` | `GET /spread?token_id=X` | Sentiment gauge: spread width → maker confidence |
| `polymarket_price_history` | `GET /prices-history?market=X&interval=I&fidelity=F` | Leading indicator: velocity + trend direction |
| `polymarket_book` | `GET /book?token_id=X` | Sentiment gauge: bid/ask imbalance → directional pressure |

实现模式: 参照现有 `getMidpoint()` 函数，纯 HTTP GET + fetchWithTimeout。

**注**: 跳过 `/data/trades` 端点（需 L2 HMAC 认证），spread + book + price_history 已足够覆盖三重角色信号。

Gateway 日志确认: `Registered 6 Polymarket tools`（原 3 + 新 3）

### Step 3: geo_briefing 复合工具 (DONE ✓ 2026-03-14)

新建文件: `findata-tools/extension/src/geo-briefing.ts` (~170 行)
改动文件: `findata-tools/extension/index.ts` (+8 行)

**参数:**
- `event_keywords` (required) — 事件关键词，用于 Twitter/News/Polymarket 搜索
- `polymarket_query` (optional) — Polymarket 专用搜索词，默认同 event_keywords
- `asset_symbols` (optional, string[]) — 资产 ticker 列表
- `market_limit` (optional, default 3) — 最多分析几个 Polymarket 盘口

**内部流程:**
```
Promise.allSettled([
  1. Twitter search (if TWITTER_TOKEN)
  2. News search (if OPENNEWS_TOKEN)
  3. Polymarket search → for top N markets, parallel fetch:
     - spread
     - price_history (interval=1d, fidelity=60)
     - book (bid/ask → pressure analysis)
  4. OpenBB stock quote × each asset_symbol
  5. OpenBB economy calendar (next 7 days)
])
→ assembleBrief(): format all results into structured sections
→ return { content: [{ type: "text", text }] }
```

**设计决策:**
- 独立 `fetchJson` helper（不 import 其他工具文件，避免耦合）
- 所有数据源用 `Promise.allSettled`，任一失败不影响其他
- 接收 `twitterToken` / `newsToken` 构造参数，由 `index.ts` 传入

**输出格式:** 纯文本分 section（Twitter Sentiment / News Coverage / Prediction Markets / Asset Prices / Economic Calendar）

Gateway 日志确认: `Registered geo_briefing composite tool`

### Step 4: 重启 & 验证 (DONE ✓ 2026-03-14)

```bash
# 重启 gateway
systemctl --user restart openclaw-gateway

# 验证日志
journalctl --user -u openclaw-gateway | grep FinData
# [FinData] Registered 3 Twitter tools
# [FinData] Registered 2 News tools
# [FinData] Registered 6 Polymarket tools      ← 3→6
# [FinData] Registered 3 OpenBB tools
# [FinData] Registered geo_briefing composite tool  ← NEW
```

所有步骤已完成，无 skillsSnapshot 残留缓存。

---

## 五、DEV_PLAN 中被省略的模块及理由

| DEV_PLAN Module | Why Skipped | Savings |
|---|---|---|
| `geo_claude_client.py` (单独调 Claude API) | main agent 自身就是 LLM，SKILL.md 指导即可 | ~200行 + API cost |
| `event_classifier.py` (Python 硬编码分类器) | LLM 按 SKILL.md 矩阵做分类，比硬编码更灵活 | ~200行 |
| `signal_extractor.py` (Python 信号提取) | 三重角色解读逻辑在 SKILL.md，LLM 解读原始数据 | ~150行 |
| `mcp_server.py` (MCP Server 封装) | 工具已作为 native tool 注册，无需额外 transport | ~250行 |
| `geo_pipeline.py` (Python 编排器) | geo_briefing TS tool 替代，更轻量 | ~150行 |
| stdio bridge 扩展 | Gateway API 直接可用 | ~100行 |
| 独立 Python 包 + pyproject.toml | 不需要额外 runtime | ~200行 |

**总节省**: ~1250 行代码，1 个 runtime 依赖

---

## 六、后续扩展点

如果 SKILL.md + 原子工具模式证明不够（例如 kimi-k2.5 分析质量不足），可渐进升级:

1. **模型升级**: 将 main agent 切换到更强模型（如 kimi-k2.5 → deepseek-reasoner for complex analysis）
2. **composite tool 内嵌 LLM 调用**: 在 `geo_briefing` 内部调用独立 LLM 做深度分析，返回结构化 JSON
3. **MCP Server 封装**: 如果需要被 Claude Desktop 等外部客户端调用，再封装
4. **历史回测**: 记录每次预测的输入/输出/实际结果，建立校准数据库

---

## 七、关键文件路径

| File | Purpose |
|------|---------|
| `.openclaw/workspace/skills/geo-analysis/SKILL.md` | Analysis framework injected into agent |
| `.openclaw/workspace/skills/geo-analysis/_meta.json` | Skill metadata |
| `.openclaw/workspace/.clawhub/lock.json` | Skill registry |
| `.openclaw/workspace/skills/findata-tools/extension/src/polymarket-tools.ts` | Polymarket tools (Step 2 改动) |
| `.openclaw/workspace/skills/findata-tools/extension/src/geo-briefing.ts` | Composite tool (Step 3 新增) |
| `.openclaw/workspace/skills/findata-tools/extension/index.ts` | Plugin entry (Step 3 改动) |
| `docs/TRADING_STRATEGY.md` | Original methodology |
| `docs/GEO_ANALYSIS_DEV_PLAN.md` | Original dev plan (superseded by this doc) |
