# 运维说明（OpenClaw Polymarket Skill）

## 1. 运行模式

- 推荐：OpenClaw 拉起 `serve-stdio` 子进程模式
- 可选：systemd 常驻 bridge（由 OpenClaw 通过 stdio/管道调用）

## 2. 关键开关

| 变量 | 默认值 | 作用 |
|------|--------|------|
| `OPENCLAW_PM_ALLOW_TRADING` | `false` | 是否允许写操作 |
| `OPENCLAW_PM_DRY_RUN` | `true` | 写操作只模拟，不真实执行 |
| `OPENCLAW_PM_MAX_AUTO_AMOUNT` | `10` | 自动交易最大 USDC 金额 |
| `OPENCLAW_PM_ENFORCE_VERSION` | `true` | 是否校验 CLI 版本 |
| `OPENCLAW_PM_CLI_VERSION` | `0.1.4` | 期望 CLI 版本 |

## 3. 安全策略

1. 生产初始必须：
   - `ALLOW_TRADING=false`
   - `DRY_RUN=true`
   - 私钥使用占位符
2. 读链路稳定后：
   - `ALLOW_TRADING=true`
   - 仍保留 `DRY_RUN=true`
3. 接入人工审批后：
   - `DRY_RUN=false`
4. 对大额交易：
   - 通过 `MAX_AUTO_AMOUNT` 限制自动执行

## 4. 监控建议

至少采集以下指标：

- `skill_call_total`（按 action 与结果分组）
- `skill_call_error_total`（按 error type 分组）
- `skill_call_duration_ms`（P50/P95/P99）
- `skill_timeout_total`
- `skill_trade_blocked_total`（被门控拦截次数）

## 5. 故障处理手册

### 5.1 `CliVersionMismatch`

- 现象：所有 action 都失败，错误类型 `CliVersionMismatch`
- 处理：
  1. `polymarket --version`
  2. 与 `OPENCLAW_PM_CLI_VERSION` 对齐
  3. 若需临时放行，设 `OPENCLAW_PM_ENFORCE_VERSION=false`

### 5.2 `BinaryNotFound`

- 现象：找不到 `polymarket` 或 `openclaw-polymarket-skill`
- 处理：
  1. 检查 `PATH`
  2. 检查 `OPENCLAW_PM_BIN`
  3. 在部署环境执行 `healthcheck`

### 5.3 写操作被拒绝

- 可能错误：
  - `TradingDisabledError`
  - `PlaceholderKeyError`
  - `HumanApprovalRequired`
- 处理：按错误类型逐项调整开关/私钥/额度阈值

### 5.4 `TimeoutError`

- 读操作：可以重试
- 写操作：不要直接重试，先查 `clob_orders`/`clob_trades` 确认是否已执行

## 6. 升级流程

1. 备份当前配置文件（特别是 `.env.openclaw`）
2. 更新代码并重新安装：

```bash
git pull
source .venv/bin/activate
pip install -e .
```

3. 运行验证：

```bash
openclaw-polymarket-skill healthcheck
openclaw-polymarket-skill list-actions
```

4. 重启 OpenClaw skill manager 或 systemd 服务

## 7. 降级流程

1. 切回上一版本代码
2. 重新安装 package
3. 重启服务
4. 执行 smoke test
