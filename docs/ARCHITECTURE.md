# 架构文档（OpenClaw Polymarket Skill）

**版本**：v0.3.0
**最后更新**：2026-03-06

---

## 1. 系统概览

`openclaw-polymarket-skill` 是 OpenClaw 的一个 **skill adapter**，将 `polymarket` CLI 封装为结构化 JSON API，并（v0.3.0 起）集成 Claude AI 分析能力。

```
┌─────────────────────────────────────────────────────┐
│                     调用方                           │
│  OpenClaw Agent  │  CLI 直接调用  │  脚本/自动化     │
└────────┬─────────┴───────┬────────┴──────┬──────────┘
         │ stdio JSON       │ subprocess    │ subprocess
         ▼                  ▼               ▼
┌────────────────────────────────────────────────────┐
│              CLI 入口层 (cli.py)                    │
│  serve-stdio │ execute │ healthcheck │ analyze      │
└──────┬───────┴────┬────┴──────┬──────┴──────┬───────┘
       │            │           │             │
       ▼            ▼           ▼             ▼
  Bridge层      Runner层    Runner层    Analyze 工作流
(bridge.py)  (runner.py)  (runner.py)  (collector→
                                        claude→report)
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

## 2. 模块层次

### 2.1 层级划分

```
接口层   cli.py  ←→  openclaw_bridge.py
            ↓
业务层   runner.py  ←→  market_collector.py
            ↓                    ↓
执行层   executor.py        claude_client.py
            ↓                    ↓
系统层   polymarket CLI    Anthropic API
```

### 2.2 模块职责一览

| 模块 | 类别 | 职责 |
|------|------|------|
| `cli.py` | 接口层 | CLI 入口，子命令路由，参数解析 |
| `openclaw_bridge.py` | 接口层 | stdio bridge，json-per-line 协议 |
| `runner.py` | 业务层 | action 路由、安全门控、版本检查 |
| `market_collector.py` | 业务层（v0.3.0）| 并行采集市场数据，编排 runner |
| `claude_client.py` | 业务层（v0.3.0）| Claude API 调用，响应解析降级 |
| `report_builder.py` | 业务层（v0.3.0）| 多格式输出构建 |
| `executor.py` | 执行层 | subprocess 调用、超时、JSON 解析 |
| `actions.py` | 配置层 | ACTION_REGISTRY，action 元数据与参数构建 |
| `settings.py` | 配置层 | 所有运行时配置，从环境变量加载 |
| `analyze_models.py` | 数据层（v0.3.0）| 分析工作流数据类 |
| `models.py` | 数据层 | bridge 请求/响应数据类 |
| `security.py` | 横切关注点 | 私钥验证、金额估算、命令脱敏 |
| `validators.py` | 横切关注点 | 参数格式校验 |
| `locks.py` | 横切关注点 | 钱包操作分布式锁 |
| `retry.py` | 横切关注点 | 指数退避重试，错误类型识别 |
| `logging_config.py` | 横切关注点 | JSON/纯文本结构化日志 |
| `errors.py` | 横切关注点 | 统一错误类型定义 |

---

## 3. 核心数据流

### 3.1 普通 execute 调用

```
cli.py
  _run_execute(args)
      ↓
  runner.execute(action, params, context)
      ├─ version check（仅首次）
      ├─ action registry lookup
      ├─ param validation
      ├─ security gate（写操作：trading enabled? dry_run? key valid? amount?）
      └─ executor.run(args, timeout)
              ↓
          subprocess: polymarket -o json <args>
              ↓
          CommandResult(ok, data, meta)
      ↓
  {"ok": true, "action": "...", "data": {...}, "meta": {...}}
```

### 3.2 analyze 工作流（v0.3.0）

```
cli.py
  _run_analyze(args)
      ↓ API key 检查（缺失 → 退出码 2）
      ↓
  MarketCollector.collect(query, market_limit)
      ├─ [串行] runner.execute("markets_search", {query, limit})
      ├─ [并行 asyncio.gather] 对每个 token_id:
      │    ├─ runner.execute("clob_midpoint", {token_id})
      │    ├─ runner.execute("clob_spread",   {token_id})
      │    ├─ runner.execute("clob_book",     {token_id})
      │    └─ runner.execute("clob_price_history", {token_id})
      └─ [可选，失败不阻塞] runner.execute("events_list", {})
      ↓
  MarketSnapshot(markets, token_data, events, fetch_errors)
      ↓ .to_summary_dict() → 去噪摘要
      ↓
  ClaudeClient.analyze(snapshot, analysis_prompt)
      ├─ 构造 system_prompt（固定角色设定）
      ├─ 构造 user_message（分析任务 + 市场数据）
      └─ Anthropic API call → 三级降级解析
      ↓
  AnalysisResult(ok, structured, report_markdown, meta)
      ↓
  report_builder.build_output(result, fmt)
      ↓
  stdout（json / markdown / both）
```

### 3.3 serve-stdio bridge

```
OpenClaw Agent
  → stdin: {"id":"req-1","method":"execute","action":"markets_search",...}
  → openclaw_bridge.py 解析行
  → runner.execute(...)
  → stdout: {"id":"req-1","ok":true,"result":{...}}
```

---

## 4. 数据模型

### 4.1 ACTION_REGISTRY（`actions.py`）

```python
ActionSpec(
    name: str,              # action 唯一标识
    category: ActionCategory,  # READ / READ_AUTH / WRITE
    required_params: tuple,  # 必填参数名
    builder: Callable,       # params → CLI args 列表
)
```

v0.3.0 支持的动作（21 个）：

| 类别 | 动作 |
|------|------|
| READ | `markets_search`, `markets_get`, `markets_list`, `events_list`, `events_get` |
| READ | `clob_book`, `clob_midpoint`, `clob_spread`, `clob_price`, `clob_price_history` |
| READ_AUTH | `clob_balance`, `clob_orders`, `clob_order` |
| READ | `data_value`, `data_trades`, `data_leaderboard` |
| WRITE | `clob_create_order`, `clob_market_order`, `clob_cancel`, `clob_cancel_orders`, `clob_cancel_all` |

### 4.2 分析工作流数据模型（v0.3.0，`analyze_models.py`）

```
TokenData
  token_id: str
  midpoint: float | None
  spread: float | None
  book: dict | None
  price_history: list | None

MarketSnapshot
  query: str
  markets: list[dict]       # 原始市场列表（来自 markets_search）
  token_data: list[TokenData]
  events: list[dict]
  fetch_errors: list[str]   # 非致命错误，不中断流程
  actions_called: int       # 总调用次数，用于 meta

  to_summary_dict() → dict  # 去噪摘要（供 Claude 使用）

AnalysisResult
  ok: bool
  query: str
  markets_analyzed: int
  structured: dict          # Claude 输出的结构化字段
  report_markdown: str      # Claude 生成的 Markdown 报告
  raw_market_data: list     # 原始市场数据
  error: str | None
  meta: dict                # duration_ms, model, tokens, actions_called 等

  to_dict() → dict          # 序列化为最终 JSON 输出
```

### 4.3 SkillSettings（`settings.py`）

```python
@dataclass(frozen=True)
class SkillSettings:
    # Polymarket CLI
    polymarket_bin: str = "polymarket"
    default_signature_type: str = "proxy"
    placeholder_private_key: str = "__PLACEHOLDER__"
    allow_trading: bool = False
    dry_run: bool = True
    max_auto_amount: float = 10.0
    read_timeout_seconds: int = 15
    write_timeout_seconds: int = 60
    cli_version: str = "0.1.4"
    enforce_cli_version: bool = True
    # v0.3.0 新增：Claude API
    anthropic_api_key: str = ""
    claude_timeout_seconds: int = 60
    claude_max_tokens: int = 4096
```

---

## 5. 安全机制

### 5.1 写操作三层门控

```
请求写操作
    ↓
[1] allow_trading == true?        → 否 → TradingDisabledError
    ↓
[2] private_key != placeholder?   → 否 → PlaceholderKeyError
    ↓
[3] dry_run == false?             → 是 → dry_run 模拟返回
    ↓
[4] amount <= max_auto_amount?    → 否 → HumanApprovalRequired
    ↓
真实执行
```

### 5.2 命令脱敏

`executor.py` 在日志中将所有敏感参数（`--private-key`, `--api-key`, `--secret`, `--password`, `--token`）替换为 `[REDACTED]`，支持 `--flag value` 和 `--flag=value` 两种格式。

### 5.3 私钥验证（`security.py`）

- 格式：必须为 `0x` + 64 位十六进制
- Placeholder 检测：9 种模式（全 0、全 f、`__PLACEHOLDER__`、`YOUR_PRIVATE_KEY` 等）

### 5.4 analyze 命令只读设计

`analyze` 工作流所有 action 均为 `READ` 类，绕过写操作门控，不需要 `POLYMARKET_PRIVATE_KEY`，不影响资金安全。

---

## 6. 错误处理策略

### 6.1 错误类型与可重试性

| 错误类型 | 可重试 | 说明 |
|----------|--------|------|
| `UnknownAction` | 否 | 不存在的 action |
| `ValidationError` | 否 | 参数格式错误 |
| `CliVersionMismatch` | 否 | CLI 版本不匹配 |
| `TradingDisabledError` | 否 | 交易功能未启用 |
| `PlaceholderKeyError` | 否 | 私钥为占位符 |
| `HumanApprovalRequired` | 否 | 超额需人工确认 |
| `TimeoutError`（读） | 是 | 网络超时，可重试 |
| `TimeoutError`（写） | 否 | 写操作超时禁止直接重试，需先查询确认 |
| `JsonParseError` | 是 | CLI 输出解析失败 |

### 6.2 analyze 工作流非致命错误

`MarketSnapshot.fetch_errors` 记录采集过程中的非阻塞错误：
- 单个 token 的 CLOB 数据失败
- `events_list` 失败

这些错误会透传到最终 JSON 输出的 `meta.fetch_errors_count`，但不影响整体 `ok` 状态（只要 Claude 分析成功）。

---

## 7. 并发模型

- `market_collector.py` 使用 `asyncio.gather` 并行发起所有 token 的 4 个 CLOB 请求
- `runner.execute()` 本身是 async，底层 `executor.run()` 通过 `asyncio.create_subprocess_exec` 启动子进程
- 写操作通过 `WalletLockManager`（`locks.py`）实现每个 wallet 的串行化，防止并发交易冲突

---

## 8. 扩展点

### 添加新 action

1. 在 `actions.py` 中添加 `build_xxx()` 函数
2. 在 `ACTION_REGISTRY` 中注册 `ActionSpec`
3. 无需修改 `runner.py` 或 `executor.py`

### 添加新输出格式

在 `report_builder.py` 的 `OutputFormat` 类型和 `build_output()` 函数中扩展，`cli.py` 的 `--output` 参数 `choices` 同步更新。

### 替换 AI 分析后端

替换 `claude_client.py` 即可（实现相同的 `analyze(snapshot, prompt) -> AnalysisResult` 接口），`report_builder.py`、`cli.py` 无需改动。

### 扩展数据采集

在 `market_collector.py` 的 `collect()` 中增加阶段或并行任务，数据自动进入 `MarketSnapshot`。

---

## 9. 目录结构

```
openclaw-polymarket-skill/
├── src/
│   └── openclaw_polymarket_skill/
│       ├── __init__.py
│       ├── cli.py                  # 接口层：CLI 入口
│       ├── openclaw_bridge.py      # 接口层：stdio bridge
│       ├── runner.py               # 业务层：action 路由与安全门控
│       ├── executor.py             # 执行层：subprocess 管理
│       ├── actions.py              # 配置层：action 元数据注册
│       ├── settings.py             # 配置层：运行时配置
│       ├── models.py               # 数据层：bridge 协议数据类
│       ├── analyze_models.py       # 数据层：分析工作流数据类（v0.3.0）
│       ├── market_collector.py     # 业务层：并行市场数据采集（v0.3.0）
│       ├── claude_client.py        # 业务层：Claude API 封装（v0.3.0）
│       ├── report_builder.py       # 业务层：多格式输出构建（v0.3.0）
│       ├── security.py             # 横切：安全校验
│       ├── validators.py           # 横切：参数校验
│       ├── locks.py                # 横切：钱包锁
│       ├── retry.py                # 横切：重试策略
│       ├── logging_config.py       # 横切：结构化日志
│       └── errors.py               # 横切：错误类型
├── tests/
│   ├── conftest.py
│   ├── test_actions.py
│   ├── test_analyze.py             # v0.3.0 新增（31 个测试）
│   ├── test_bridge.py
│   ├── test_retry.py
│   ├── test_runner.py
│   ├── test_security.py
│   └── test_validators.py
├── openclaw/
│   ├── .env.openclaw.template
│   ├── openclaw-skill-config.template.json
│   └── bridge-request-examples.jsonl
├── docs/
│   ├── ARCHITECTURE.md             # 本文档
│   ├── DEPLOYMENT.md
│   ├── OPENCLAW_INTEGRATION.md
│   ├── OPERATIONS.md
│   └── plan.md
├── pyproject.toml
└── CHANGELOG.md
```

---

## 10. 版本演进

| 版本 | 关键变化 |
|------|----------|
| v0.1.0 | 21 个原子 action，stdio bridge，基础安全机制 |
| v0.2.0 | 结构化日志、指数退避重试、增强命令脱敏、强化私钥验证 |
| v0.3.0 | `analyze` 端到端分析工作流，Claude AI 集成，并行数据采集，多格式报告输出 |
