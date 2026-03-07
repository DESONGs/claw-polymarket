# OpenClaw Polymarket Skill

> **OpenClaw** 的 Polymarket 预测市场 skill 适配器 — 将 `polymarket-cli` 封装为结构化 JSON API，并集成 Claude AI 分析能力，支持自然语言驱动的市场搜索与概率解读。

[![version](https://img.shields.io/badge/version-0.3.1-blue)](#) [![python](https://img.shields.io/badge/python-3.10%2B-blue)](#) [![polymarket--cli](https://img.shields.io/badge/polymarket--cli-0.1.4-green)](#) [![license](https://img.shields.io/badge/license-MIT-green)](#)

---

## 目录

- [功能概览](#功能概览)
- [快速开始](#快速开始)
- [架构说明](#架构说明)
- [安装](#安装)
- [环境变量](#环境变量)
- [CLI 命令参考](#cli-命令参考)
- [支持的 Actions](#支持的-actions)
- [AI 分析工作流](#ai-分析工作流)
- [OpenClaw 对接](#openclaw-对接)
- [安全机制](#安全机制)
- [测试](#测试)
- [文档](#文档)
- [更新日志](#更新日志)

---

## 功能概览

| 能力 | 说明 |
|------|------|
| **21 个原子 Action** | 市场查询、CLOB 行情、交易下单、数据统计，统一 JSON 输出 |
| **AI 分析工作流** | 一键采集市场数据并调用 Claude 生成结构化分析报告 |
| **自然语言查询** | 搜索任意关键词（如"伊朗"、"原油"），自动匹配相关预测事件 |
| **安全写操作门控** | 四层防护：交易开关 → 占位私钥检测 → dry-run → 金额上限 |
| **OpenClaw 桥接** | stdio json-per-line 协议，供 Agent 框架直接调用 |
| **并行数据采集** | `asyncio.gather` 并发拉取盘口/价差/委托簿/历史价格 |

---

## 快速开始

### 1. 安装依赖

```bash
# 安装 polymarket CLI（macOS arm64 示例）
curl -L https://github.com/Polymarket/polymarket-cli/releases/download/v0.1.4/polymarket-v0.1.4-aarch64-apple-darwin.tar.gz \
  | tar -xz -C /usr/local/bin/

# 安装 skill
git clone https://github.com/DESONGs/claw-polymarket.git
cd claw-polymarket
pip install -e .
```

### 2. 搜索预测市场

```bash
# 搜索伊朗相关事件
openclaw-polymarket-skill execute \
  --action markets_search \
  --params '{"query":"Iran","limit":5}'
```

### 3. 查询市场概率（midpoint）

```bash
# 查询某个 token 的市场隐含概率
openclaw-polymarket-skill execute \
  --action clob_midpoint \
  --params '{"token_id":"0x2c2a110ac348e3ed660da6450f51f1b51d5bd4704d43d66e810669cf2b9b6927"}'
# 返回: {"midpoint": "0.9995"}  → 市场认为该事件发生概率约 99.95%
```

### 4. AI 智能分析

```bash
export ANTHROPIC_API_KEY=sk-ant-xxxxx

openclaw-polymarket-skill analyze \
  --query "crude oil" \
  --analysis-prompt "找寻和原油相关的预测事件，并告诉我每个事件市场认为的概率" \
  --market-limit 5 \
  --output markdown
```

---

## 架构说明

```
┌─────────────────────────────────────────────────────┐
│                      调用方                          │
│   OpenClaw Agent  │  CLI 直接调用  │  脚本/自动化    │
└────────┬──────────┴───────┬────────┴──────┬──────────┘
         │ stdio JSON        │ subprocess    │ subprocess
         ▼                   ▼               ▼
┌────────────────────────────────────────────────────┐
│             CLI 入口层  (cli.py)                    │
│  serve-stdio │ execute │ healthcheck │ analyze      │
└──────┬───────┴────┬────┴──────┬──────┴──────┬───────┘
       │            │           │             │
  Bridge 层    Runner 层    Runner 层   Analyze 工作流
(bridge.py)  (runner.py)  (runner.py)   collector →
                                        claude → report
       │            │                        │
       └────────────┴────────────────────────┘
                         │
                    Executor 层
                   (executor.py)
                         │
              ┌──────────┴──────────┐
              ▼                     ▼
        polymarket CLI         Anthropic API
        (本地二进制)            (外部 HTTP)
```

---

## 安装

### 系统要求

- Python 3.10+
- `polymarket` CLI 二进制在 `PATH` 中（版本 0.1.4）

### 安装 polymarket CLI

```bash
# macOS arm64
curl -L https://github.com/Polymarket/polymarket-cli/releases/download/v0.1.4/polymarket-v0.1.4-aarch64-apple-darwin.tar.gz \
  | tar -xz -C /usr/local/bin/

# macOS x86_64
curl -L https://github.com/Polymarket/polymarket-cli/releases/download/v0.1.4/polymarket-v0.1.4-x86_64-apple-darwin.tar.gz \
  | tar -xz -C /usr/local/bin/

# Linux x86_64
curl -L https://github.com/Polymarket/polymarket-cli/releases/download/v0.1.4/polymarket-v0.1.4-x86_64-unknown-linux-gnu.tar.gz \
  | tar -xz -C /usr/local/bin/
```

### 安装 skill

```bash
git clone https://github.com/DESONGs/claw-polymarket.git
cd claw-polymarket

# 生产安装
pip install -e .

# 开发安装（含测试依赖）
pip install -e ".[dev]"
```

### 验证安装

```bash
openclaw-polymarket-skill healthcheck
# {"ok": true, "version": "0.1.4", "error": null}
```

---

## 环境变量

### Polymarket CLI 配置

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `OPENCLAW_PM_BIN` | `polymarket` | polymarket CLI 二进制路径 |
| `OPENCLAW_PM_CLI_VERSION` | `0.1.4` | 期望的 CLI 版本号 |
| `OPENCLAW_PM_ENFORCE_VERSION` | `true` | 是否强制版本检查 |
| `OPENCLAW_PM_ALLOW_TRADING` | `false` | 是否允许真实交易 |
| `OPENCLAW_PM_DRY_RUN` | `true` | dry-run 模式（不真实下单） |
| `OPENCLAW_PM_MAX_AUTO_AMOUNT` | `10` | 自动执行金额上限（USD） |
| `OPENCLAW_PM_READ_TIMEOUT_SECONDS` | `15` | 读操作超时（秒） |
| `OPENCLAW_PM_WRITE_TIMEOUT_SECONDS` | `60` | 写操作超时（秒） |

### 交易身份配置（写操作必填）

| 变量 | 说明 |
|------|------|
| `POLYMARKET_PRIVATE_KEY` | 钱包私钥（`0x` + 64位十六进制） |
| `POLYMARKET_SIGNATURE_TYPE` | 签名类型，默认 `proxy` |

### AI 分析配置（`analyze` 子命令必填）

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `ANTHROPIC_API_KEY` | 空 | Claude API 密钥 |
| `OPENCLAW_CLAUDE_TIMEOUT` | `60` | Claude API 超时（秒） |
| `OPENCLAW_CLAUDE_MAX_TOKENS` | `4096` | Claude 最大输出 tokens |

可参考 `openclaw/.env.openclaw.template` 进行配置。

---

## CLI 命令参考

### `healthcheck` — 健康检查

```bash
openclaw-polymarket-skill healthcheck
```

```json
{"ok": true, "version": "0.1.4", "error": null}
```

### `list-actions` — 列出所有 actions

```bash
openclaw-polymarket-skill list-actions
```

### `execute` — 执行单个 action

```bash
openclaw-polymarket-skill execute \
  --action <action_name> \
  --params '<JSON 对象>' \
  --context '<JSON 对象>'   # 可选，交易时传入 private_key 等
```

**示例：搜索市场**

```bash
openclaw-polymarket-skill execute \
  --action markets_search \
  --params '{"query": "Iran", "limit": 5}'
```

**示例：查询价格概率**

```bash
openclaw-polymarket-skill execute \
  --action clob_midpoint \
  --params '{"token_id": "0x2c2a110ac348e3ed660da6450f51f1b51d5bd4704d43d66e810669cf2b9b6927"}'
```

**示例：模拟下单（dry-run）**

```bash
OPENCLAW_PM_ALLOW_TRADING=true \
openclaw-polymarket-skill execute \
  --action clob_create_order \
  --params '{"token":"48331043336612883","side":"buy","price":"0.50","size":"10"}' \
  --context '{"private_key":"__PLACEHOLDER__","wallet_id":"demo-user"}'
```

### `analyze` — AI 分析工作流

```bash
openclaw-polymarket-skill analyze \
  --query "crude oil" \
  --analysis-prompt "找寻和原油相关的预测事件，并告诉我每个事件市场认为的概率" \
  --market-limit 5 \
  --output both
```

| 参数 | 必填 | 说明 |
|------|------|------|
| `--query` | 是 | 搜索关键词 |
| `--analysis-prompt` | 是 | 传给 Claude 的分析指令 |
| `--market-limit` | 否 | 最多分析的市场数量，默认 5 |
| `--output` | 否 | 输出格式：`json` / `markdown` / `both`，默认 `both` |

### `serve-stdio` — OpenClaw 桥接模式

```bash
openclaw-polymarket-skill serve-stdio
```

stdin 按行输入 JSON 请求：

```json
{"id":"1","method":"healthcheck"}
{"id":"2","method":"list_actions"}
{"id":"3","method":"execute","action":"markets_search","params":{"query":"bitcoin","limit":5},"context":{}}
```

---

## 支持的 Actions

### 市场信息（READ）

| Action | 必填参数 | 说明 |
|--------|----------|------|
| `markets_search` | `query` | 关键词搜索市场 |
| `markets_get` | `id_or_slug` | 获取单个市场详情 |
| `markets_list` | — | 列出市场（支持过滤排序） |
| `events_list` | — | 列出事件 |
| `events_get` | `id` | 获取单个事件详情 |

### CLOB 行情（READ）

| Action | 必填参数 | 说明 |
|--------|----------|------|
| `clob_midpoint` | `token_id` | 查询 token 中间价（即市场隐含概率） |
| `clob_spread` | `token_id` | 查询买卖价差 |
| `clob_book` | `token_id` | 查询完整委托簿 |
| `clob_price` | `token_id`, `side` | 查询买入/卖出价格 |
| `clob_price_history` | `token_id` | 查询历史价格 |

> **注意**：`token_id` 支持纯数字格式（如 `48331043`）和十六进制格式（如 `0x2c2a110a...`），两者均有效。

### CLOB 账户（READ_AUTH）

| Action | 必填参数 | 说明 |
|--------|----------|------|
| `clob_balance` | `asset_type` | 查询余额 |
| `clob_orders` | — | 查询挂单列表 |
| `clob_order` | `order_id` | 查询单个挂单 |

### 交易操作（WRITE）

| Action | 必填参数 | 说明 |
|--------|----------|------|
| `clob_create_order` | `token`, `side`, `price`, `size` | 限价下单 |
| `clob_market_order` | `token`, `side`, `amount` | 市价下单 |
| `clob_cancel` | `order_id` | 撤单 |
| `clob_cancel_orders` | `order_ids` | 批量撤单 |
| `clob_cancel_all` | — | 撤销全部挂单 |

### 数据统计（READ）

| Action | 必填参数 | 说明 |
|--------|----------|------|
| `data_positions` | `address` | 查询持仓 |
| `data_value` | `address` | 查询账户净值 |
| `data_trades` | `address` | 查询交易记录 |
| `data_leaderboard` | — | 查询排行榜 |

---

## AI 分析工作流

`analyze` 子命令实现了完整的端到端分析流程：

```
搜索关键词
    ↓
markets_search（获取市场列表）
    ↓
asyncio.gather 并行采集（每个 token）：
    ├─ clob_midpoint  → 市场隐含概率
    ├─ clob_spread    → 买卖价差
    ├─ clob_book      → 委托簿深度
    └─ clob_price_history → 历史走势
    ↓
MarketSnapshot（结构化快照）
    ↓
Claude API（角色：专业预测市场分析师）
    ↓
输出：JSON 结构化数据 + Markdown 分析报告
```

### 实际测试示例

**测试指令**：找寻伊朗相关的热门预测事件，并说明每个事件不同选项的价格

| 事件 | YES | NO | 流动性 |
|------|-----|-----|--------|
| Will Iran strike Israel on March 4? | 99.95% | 0.05% | $3,241,804 |
| Will Iran strike Israel on March 3? | 99.95% | 0.05% | $1,865,350 |
| Will Iran strike Israel on March 10? | 45.5% | 54.5% | $11,228 |

**测试指令**：找寻和原油相关的预测事件，并告诉我每个事件市场认为的概率

| 事件（3月底） | YES 概率 | NO 概率 | 流动性 |
|--------------|---------|---------|--------|
| Crude Oil 触及 HIGH $200 | 5.2% | 94.8% | $87,193 |
| Crude Oil 触及 HIGH $180 | 5.9% | 94.1% | $89,258 |
| Crude Oil 触及 HIGH $150 | 14.2% | 85.8% | $73,727 |
| Crude Oil 触及 HIGH $100 | **79.5%** | 20.5% | $71,176 |
| Crude Oil 触及 HIGH $110 | **55.0%** | 45.0% | $32,747 |
| Crude Oil 跌至 LOW $65 | 9.5% | 90.5% | $32,867 |
| Crude Oil 跌至 LOW $50 | 1.5% | 98.5% | $26,853 |
| Crude Oil 跌至 LOW $40 | 0.4% | 99.6% | $23,748 |

---

## OpenClaw 对接

### 注册 Skill

使用项目根目录的 `skill.manifest.json`：

```json
{
  "name": "polymarket",
  "version": "0.1.0",
  "description": "OpenClaw skill adapter for polymarket-cli",
  "bridge_entrypoint": "openclaw-polymarket-skill serve-stdio",
  "bridge_protocol": "json-per-line",
  "actions": ["markets_search", "clob_midpoint", "clob_create_order", ...]
}
```

### 推荐下单流程

```
1. markets_search  → 找到目标市场
2. markets_get     → 确认市场详情
3. clob_book / clob_spread  → 评估流动性
4. clob_balance    → 确认账户余额
5. clob_create_order / clob_market_order  → 执行下单（需人工二次确认）
```

> 写操作超时后，**禁止直接重试**，应先通过 `clob_orders` / `data_trades` 查询确认是否成交。

---

## 安全机制

### 写操作四层门控

```
请求写操作
    ↓
[1] OPENCLAW_PM_ALLOW_TRADING == true?  → 否 → TradingDisabledError
    ↓
[2] private_key != placeholder?         → 否 → PlaceholderKeyError
    ↓
[3] dry_run == false?                   → 是 → dry-run 模拟响应
    ↓
[4] amount <= max_auto_amount?          → 否 → HumanApprovalRequired
    ↓
真实执行
```

### 私钥保护

- 9 种 placeholder 模式检测（`__PLACEHOLDER__`、全零、全 `f`、`YOUR_PRIVATE_KEY` 等）
- 日志输出中所有敏感参数自动脱敏为 `[REDACTED]`
- 私钥仅通过运行时 `context` 传入，不进入持久化存储

---

## 测试

```bash
# 运行全部测试
pytest -q

# 生成覆盖率报告
pytest --cov=openclaw_polymarket_skill --cov-report=html

# 健康检查（需 polymarket CLI 已安装）
openclaw-polymarket-skill healthcheck
```

---

## 文档

| 文档 | 说明 |
|------|------|
| `docs/ARCHITECTURE.md` | 系统架构、模块层次、数据流、数据模型 |
| `docs/DEPLOYMENT.md` | 部署指南（本机 / 服务器 / systemd） |
| `docs/OPERATIONS.md` | 运维手册（监控、排障、升级回滚） |
| `openclaw/OPENCLAW_INTEGRATION.md` | OpenClaw 框架对接详细说明 |
| `action_schemas.json` | 所有 action 参数的 JSON Schema |

---

## 更新日志

### v0.3.1（2026-03-07）

- **修复**：`token_id` 参数校验正则更新，同时支持十六进制格式（`0x...`）和纯数字格式，与 `polymarket-cli` 实际行为对齐

### v0.3.0（2026-03-06）

- 新增 `analyze` 端到端 AI 分析子命令
- 集成 Claude API，支持自然语言市场分析
- 并行市场数据采集（`asyncio.gather`）
- 多格式报告输出（JSON / Markdown / both）

### v0.2.0（2026-03-02）

- 结构化日志（JSON/纯文本）
- 指数退避智能重试
- 增强命令脱敏与私钥验证

### v0.1.0

- 21 个原子 Action
- stdio bridge 桥接模式
- 写操作安全门控

完整更新历史见 [CHANGELOG.md](CHANGELOG.md)。

---

## License

MIT
