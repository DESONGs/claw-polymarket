# 部署文档（OpenClaw Polymarket Skill）

## 变更历史

| 版本 | 日期 | 变更摘要 |
|------|------|---------|
| v0.3.0 | 2026-03-06 | 新增 `analyze` 子命令，需配置 `ANTHROPIC_API_KEY` |
| v0.2.0 | 2026-03-02 | 安全增强、结构化日志、重试机制 |
| v0.1.0 | — | 初始版本 |

---

## 1. 目标

将 `openclaw-polymarket-skill` 部署到可被 OpenClaw 调用的运行环境，以 `stdio bridge` 模式提供服务，并可选启用 `analyze` AI 分析功能。

---

## 2. 前置条件

| 要求 | 说明 |
|------|------|
| Python 3.10+ | 必须 |
| `polymarket` CLI | 二进制名 `polymarket`，版本需与 `OPENCLAW_PM_CLI_VERSION`（默认 `0.1.4`）对齐 |
| 网络访问 Polymarket API | 用于市场数据查询 |
| `ANTHROPIC_API_KEY` | **v0.3.0 新增**，仅 `analyze` 子命令需要，其他命令无需此项 |

---

## 3. 本机部署（推荐先做）

```bash
cd openclaw-polymarket-skill
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
cp openclaw/.env.openclaw.template openclaw/.env.openclaw
```

编辑 `openclaw/.env.openclaw`，填写必要参数（特别是 v0.3.0 新增项）：

```bash
# 基础配置（原有）
OPENCLAW_PM_BIN=polymarket
OPENCLAW_PM_CLI_VERSION=0.1.4
POLYMARKET_PRIVATE_KEY=__PLACEHOLDER__

# v0.3.0 新增：AI 分析功能（analyze 命令专用）
ANTHROPIC_API_KEY=sk-ant-...        # 必填，否则 analyze 退出码 2
OPENCLAW_CLAUDE_TIMEOUT=60          # 可选，默认 60 秒
OPENCLAW_CLAUDE_MAX_TOKENS=4096     # 可选，默认 4096 tokens
```

基础验证：

```bash
openclaw-polymarket-skill healthcheck
openclaw-polymarket-skill list-actions
```

analyze 功能验证（需真实 API key）：

```bash
openclaw-polymarket-skill analyze \
  --query "bitcoin" \
  --analysis-prompt "分析这个市场的流动性" \
  --market-limit 2 \
  --output json
```

---

## 4. 服务器部署（systemd）

### 4.1 目录准备

```bash
sudo mkdir -p /opt/openclaw-polymarket-skill
sudo chown -R $USER:$USER /opt/openclaw-polymarket-skill
cp -R openclaw-polymarket-skill/* /opt/openclaw-polymarket-skill/
cd /opt/openclaw-polymarket-skill
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
cp openclaw/.env.openclaw.template openclaw/.env.openclaw
# 编辑 .env.openclaw，填写 ANTHROPIC_API_KEY 等
```

### 4.2 systemd 服务文件

创建 `/etc/systemd/system/openclaw-polymarket-skill.service`：

```ini
[Unit]
Description=OpenClaw Polymarket Skill Bridge
After=network.target

[Service]
Type=simple
User=YOUR_USER
WorkingDirectory=/opt/openclaw-polymarket-skill
EnvironmentFile=/opt/openclaw-polymarket-skill/openclaw/.env.openclaw
ExecStart=/opt/openclaw-polymarket-skill/.venv/bin/openclaw-polymarket-skill serve-stdio
Restart=always
RestartSec=2

[Install]
WantedBy=multi-user.target
```

> **说明**：`serve-stdio` bridge 模式不需要 `ANTHROPIC_API_KEY`（`analyze` 命令通过 CLI 直接调用，不经过 bridge）。如需通过自动化脚本调用 `analyze`，在 `EnvironmentFile` 中配置即可。

启动服务：

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now openclaw-polymarket-skill
sudo systemctl status openclaw-polymarket-skill
```

---

## 5. OpenClaw 侧接入

1. 复制 `openclaw/openclaw-skill-config.template.json` 到 OpenClaw 的 skill 配置目录
2. 修改 `command` 为实际路径（如 `/opt/openclaw-polymarket-skill/.venv/bin/openclaw-polymarket-skill`）
3. 修改 `cwd` 为部署目录
4. 重启 OpenClaw skill manager

> **v0.3.0 注意**：`analyze` 命令是独立 CLI 命令，不通过 OpenClaw bridge 协议调用，需直接在 shell 中执行。

---

## 6. 发布流程（v0.3.0）

1. **测试环境验证**：
   - `healthcheck` 成功
   - `markets_search` 成功
   - `analyze` 命令（无 API key）退出码为 `2`
   - `analyze` 命令（有 API key）正常返回 JSON

2. **灰度策略**：
   - 先只读（`ALLOW_TRADING=false`），验证 `analyze` 数据采集稳定性
   - 观察 Claude API 延迟和 token 用量（查看 `meta.duration_ms` 和 `meta.input_tokens`）
   - 稳定后再逐步放开交易功能

3. **全量发布**：错误率和超时率达标后全量。

---

## 7. 回滚方案

若 v0.3.0 异常需回滚到 v0.2.0：

```bash
git checkout v0.2.0          # 或回滚代码目录
pip install -e .
sudo systemctl restart openclaw-polymarket-skill
```

验证：

```bash
openclaw-polymarket-skill healthcheck
openclaw-polymarket-skill list-actions
# analyze 命令在 v0.2.0 不存在，正常
```

> **注意**：v0.2.0 的 `settings.py` 没有 Claude 相关字段，`.env.openclaw` 中的 `ANTHROPIC_API_KEY` 等配置会被忽略，不会影响回滚后的运行。

---

## 8. 环境变量完整参考（v0.3.0）

| 变量 | 默认值 | 必填 | 说明 |
|------|--------|------|------|
| `OPENCLAW_PM_BIN` | `polymarket` | 否 | polymarket CLI 路径 |
| `OPENCLAW_PM_CLI_VERSION` | `0.1.4` | 否 | 期望 CLI 版本 |
| `OPENCLAW_PM_ENFORCE_VERSION` | `true` | 否 | 是否校验 CLI 版本 |
| `OPENCLAW_PM_ALLOW_TRADING` | `false` | 否 | 是否允许写操作 |
| `OPENCLAW_PM_DRY_RUN` | `true` | 否 | 写操作只模拟 |
| `OPENCLAW_PM_MAX_AUTO_AMOUNT` | `10` | 否 | 自动交易最大 USDC |
| `OPENCLAW_PM_READ_TIMEOUT_SECONDS` | `15` | 否 | 读操作超时（秒） |
| `OPENCLAW_PM_WRITE_TIMEOUT_SECONDS` | `60` | 否 | 写操作超时（秒） |
| `POLYMARKET_PRIVATE_KEY` | `__PLACEHOLDER__` | 交易时必填 | 钱包私钥 |
| `POLYMARKET_SIGNATURE_TYPE` | `proxy` | 否 | 签名类型 |
| `ANTHROPIC_API_KEY` | `""` | **analyze 必填** | Claude API 密钥 |
| `OPENCLAW_CLAUDE_TIMEOUT` | `60` | 否 | Claude 调用超时（秒） |
| `OPENCLAW_CLAUDE_MAX_TOKENS` | `4096` | 否 | Claude 最大输出 tokens |
