# OpenClaw Polymarket Skill

独立的 OpenClaw Skill 适配项目，通过子进程调用 `polymarket-cli`，提供 Polymarket 信息查询与交易操作。

## 功能概览

- 统一调用 `polymarket -o json ...`
- 读写动作分级控制（`read` / `read_auth` / `write`）
- 写操作安全门控：
  - `OPENCLAW_PM_ALLOW_TRADING`
  - 占位私钥检测
  - `OPENCLAW_PM_DRY_RUN`
  - `OPENCLAW_PM_MAX_AUTO_AMOUNT`
- 参数校验、错误分类、命令脱敏
- per-wallet 并发锁（写操作串行）

## 项目结构

```text
openclaw-polymarket-skill/
  src/openclaw_polymarket_skill/
    actions.py
    cli.py
    errors.py
    executor.py
    locks.py
    models.py
    runner.py
    security.py
    settings.py
    validators.py
  action_schemas.json
  skill.manifest.json
  tests/
```

## 环境要求

- Python 3.10+
- `polymarket` 二进制在 `PATH` 中
- 建议固定 CLI 版本：`0.1.4`

## 安装

```bash
cd openclaw-polymarket-skill
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

## 环境变量

```bash
export OPENCLAW_PM_BIN=polymarket
export OPENCLAW_PM_CLI_VERSION=0.1.4
export OPENCLAW_PM_ENFORCE_VERSION=true
export OPENCLAW_PM_ALLOW_TRADING=false
export OPENCLAW_PM_DRY_RUN=true
export OPENCLAW_PM_MAX_AUTO_AMOUNT=10
```

可选：

```bash
export POLYMARKET_PRIVATE_KEY=__PLACEHOLDER__
export POLYMARKET_SIGNATURE_TYPE=proxy
```

## 命令行使用

### 1) 健康检查

```bash
openclaw-polymarket-skill healthcheck
```

### 2) 列出动作

```bash
openclaw-polymarket-skill list-actions
```

### 3) 执行动作

```bash
openclaw-polymarket-skill execute \
  --action markets_search \
  --params '{"query":"bitcoin","limit":5}'
```

### 4) 交易动作（默认 dry-run）

```bash
openclaw-polymarket-skill execute \
  --action clob_create_order \
  --params '{"token":"48331043336612883","side":"buy","price":"0.50","size":"10"}' \
  --context '{"private_key":"__PLACEHOLDER__","wallet_id":"demo-user"}'
```

### 5) OpenClaw 直接桥接模式（stdio）

```bash
openclaw-polymarket-skill serve-stdio
```

可以从 stdin 按行写入 JSON 请求，例如：

```json
{"id":"1","method":"healthcheck"}
{"id":"2","method":"list_actions"}
{"id":"3","method":"execute","action":"markets_search","params":{"query":"bitcoin","limit":5},"context":{}}
```

## OpenClaw 对接建议

- 使用 `skill.manifest.json` 注册 skill 元信息
- 使用 `action_schemas.json` 作为动作参数约束
- 使用 `openclaw/openclaw-skill-config.template.json` 作为 OpenClaw 配置模板
- 写操作在 Agent 层要求用户二次确认
- 下单前固定流程：
  1. `markets_search`
  2. `markets_get`
  3. `clob_book` / `clob_spread`
  4. `clob_balance`
  5. `clob_create_order` / `clob_market_order`

## 文档

- `docs/OPENCLAW_INTEGRATION.md`：OpenClaw 对接说明
- `docs/DEPLOYMENT.md`：部署文档（本机 / 服务器 / systemd）
- `docs/OPERATIONS.md`：运维手册（监控、排障、升级回滚）

## 测试

```bash
pytest -q
```

## 注意事项

- JSON 模式错误通常在 stdout，而不是 stderr
- 非幂等写操作超时后不要自动重试，应先查询 `clob_orders` / `clob_trades`
- 请勿在日志里输出原始私钥
