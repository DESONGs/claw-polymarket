# OpenClaw 对接说明（可直接使用）

本文档说明如何把 `openclaw-polymarket-skill` 直接接入 OpenClaw。

## 1. 对接方式

本项目提供 `stdio bridge` 模式，适合 OpenClaw 以子进程方式管理 skill：

- 启动命令：`openclaw-polymarket-skill serve-stdio`
- 交互协议：每行一个 JSON 请求/响应（`json-per-line`）

## 2. 目录与文件

- 对接配置模板：`openclaw/openclaw-skill-config.template.json`
- 环境变量模板：`openclaw/.env.openclaw.template`
- 请求示例：`openclaw/bridge-request-examples.jsonl`
- 启动脚本：`scripts/run_openclaw_bridge.sh`

## 3. OpenClaw 配置步骤

1. 复制配置模板到你的 OpenClaw 配置目录：

```bash
cp openclaw/openclaw-skill-config.template.json /path/to/openclaw/skills/polymarket.json
```

2. 修改配置中的 `cwd` 为本项目绝对路径。

3. 复制环境模板：

```bash
cp openclaw/.env.openclaw.template openclaw/.env.openclaw
```

4. 根据环境调整以下变量：

- `OPENCLAW_PM_BIN`
- `OPENCLAW_PM_CLI_VERSION`
- `OPENCLAW_PM_ALLOW_TRADING`
- `OPENCLAW_PM_DRY_RUN`
- `OPENCLAW_PM_MAX_AUTO_AMOUNT`
- `POLYMARKET_PRIVATE_KEY`
- `POLYMARKET_SIGNATURE_TYPE`

5. 在 OpenClaw 里重载 skill registry。

## 4. Bridge 协议

### 4.1 请求

```json
{
  "id": "req-1",
  "method": "execute",
  "action": "markets_search",
  "params": {
    "query": "bitcoin",
    "limit": 5
  },
  "context": {}
}
```

### 4.2 响应

```json
{
  "id": "req-1",
  "ok": true,
  "result": {
    "ok": true,
    "action": "markets_search",
    "data": [],
    "meta": {
      "action": "markets_search",
      "cmd_sanitized": ["polymarket", "-o", "json", "markets", "search", "bitcoin", "--limit", "5"],
      "duration_ms": 120
    }
  }
}
```

### 4.3 支持的 method

- `healthcheck`
- `list_actions`
- `execute`

## 5. 交易安全建议

生产默认建议：

- `OPENCLAW_PM_ALLOW_TRADING=false`
- `OPENCLAW_PM_DRY_RUN=true`
- `POLYMARKET_PRIVATE_KEY=__PLACEHOLDER__`

逐步启用流程：

1. 先只开读操作（验证调用稳定性）
2. 开 `ALLOW_TRADING=true` 但仍 `DRY_RUN=true`
3. 接入人工确认流程后再 `DRY_RUN=false`
4. 配置真实私钥并启用额度阈值

## 6. 常见问题

### 6.1 OpenClaw 报 skill 不可用

- 检查 `openclaw-polymarket-skill` 是否在 `PATH`
- 检查 `cwd` 是否正确
- 先执行：`openclaw-polymarket-skill healthcheck`

### 6.2 请求超时

- 增大 `OPENCLAW_PM_READ_TIMEOUT_SECONDS` 或 `OPENCLAW_PM_WRITE_TIMEOUT_SECONDS`
- 检查外网连接到 Polymarket API 是否正常

### 6.3 交易被拒绝

按顺序检查：

1. `OPENCLAW_PM_ALLOW_TRADING` 是否为 `true`
2. 私钥是否仍为占位符
3. 是否命中 `OPENCLAW_PM_MAX_AUTO_AMOUNT` 阈值
