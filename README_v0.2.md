# OpenClaw Polymarket Skill

[![Version](https://img.shields.io/badge/version-0.2.0-blue.svg)](https://github.com/DESONGs/claw-polymarket)
[![Python](https://img.shields.io/badge/python-3.10+-green.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-MIT-orange.svg)](LICENSE)
[![Tests](https://img.shields.io/badge/tests-passing-brightgreen.svg)]()
[![Coverage](https://img.shields.io/badge/coverage-70%25+-green.svg)]()

独立的 OpenClaw Skill 适配项目，通过子进程调用 `polymarket-cli`，提供 Polymarket 信息查询与交易操作。

## ✨ 功能概览

### 核心功能
- 统一调用 `polymarket -o json ...`
- 读写动作分级控制（`read` / `read_auth` / `write`）
- 写操作安全门控：
  - `OPENCLAW_PM_ALLOW_TRADING`
  - 增强的占位私钥检测
  - `OPENCLAW_PM_DRY_RUN`
  - `OPENCLAW_PM_MAX_AUTO_AMOUNT`
- 参数校验、错误分类、增强的命令脱敏
- per-wallet 并发锁（写操作串行）

### 🆕 v0.2.0 新功能

#### 增强的安全机制
- ✅ **完善的命令脱敏**: 支持 `--flag=value` 和 `--flag value` 两种格式
- ✅ **严格的私钥验证**: 64位十六进制格式验证，扩展的 placeholder 检测（9种模式）
- ✅ **多种敏感参数保护**: `--private-key`, `--api-key`, `--secret`, `--password`, `--token`

#### 可靠性提升
- ✅ **智能重试机制**: 指数退避算法，自动识别可重试错误，支持抖动避免雷鸣效应
- ✅ **完善的错误处理**: 超时显式终止进程，完整保留诊断信息
- ✅ **空响应检测**: 避免静默失败
- ✅ **统一的时间追踪**: 准确的执行时长统计

#### 可观测性
- ✅ **结构化日志**: 支持 JSON 和纯文本两种格式
- ✅ **详细的执行元数据**: 时长追踪、错误分类、stdout/stderr 完整保留

#### 测试覆盖
- ✅ **完整的单元测试套件**: 覆盖率 70%+
- ✅ **自动化测试**: pytest + pytest-asyncio + pytest-cov
- ✅ **Security 模块**: 覆盖率 90%+
- ✅ **Retry 模块**: 覆盖率 95%+

## 项目结构

```text
openclaw-polymarket-skill/
  src/openclaw_polymarket_skill/
    actions.py          # 动作定义
    cli.py              # CLI 入口
    errors.py           # 错误分类
    executor.py         # 命令执行器 (✨ 改进)
    locks.py            # 并发锁
    logging_config.py   # 🆕 结构化日志
    models.py           # 数据模型
    retry.py            # 🆕 重试机制
    runner.py           # 动作执行器
    security.py         # 安全模块 (✨ 增强)
    settings.py         # 配置管理
    validators.py       # 参数验证
  action_schemas.json   # 动作参数约束
  skill.manifest.json   # Skill 元信息
  tests/                # 🆕 完整测试套件
    conftest.py
    test_security.py    # Security 测试
    test_retry.py       # 🆕 Retry 测试
    test_actions.py
    test_runner.py
    test_validators.py
  docs/
    OPENCLAW_INTEGRATION.md
    DEPLOYMENT.md
    OPERATIONS.md
  ITERATION_DEV_DOC.md  # 🆕 迭代开发文档
  CHANGELOG.md          # 🆕 变更日志
  pytest.ini            # 🆕 测试配置
```

## 环境要求

- Python 3.10+
- `polymarket` 二进制在 `PATH` 中
- 建议固定 CLI 版本：`0.1.4`

## 安装

```bash
cd openclaw-polymarket-skill
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# 生产环境
pip install -e .

# 开发环境（包含测试工具）
pip install -e ".[dev]"
```

## 环境变量

### 必需配置
```bash
export OPENCLAW_PM_BIN=polymarket
export OPENCLAW_PM_CLI_VERSION=0.1.4
export OPENCLAW_PM_ENFORCE_VERSION=true
```

### 安全配置
```bash
export OPENCLAW_PM_ALLOW_TRADING=false  # 是否允许真实交易
export OPENCLAW_PM_DRY_RUN=true         # Dry-run 模式
export OPENCLAW_PM_MAX_AUTO_AMOUNT=10   # 最大自动交易金额
```

### 可选配置
```bash
export POLYMARKET_PRIVATE_KEY=0x...     # 私钥（请使用环境变量或密钥管理服务）
export POLYMARKET_SIGNATURE_TYPE=proxy  # 签名类型
```

### 🆕 日志配置
```bash
export OPENCLAW_PM_LOG_LEVEL=INFO       # DEBUG, INFO, WARNING, ERROR
export OPENCLAW_PM_LOG_FORMAT=json      # json 或 text
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
  1. `markets_search` - 搜索市场
  2. `markets_get` - 获取市场详情
  3. `clob_book` / `clob_spread` - 查看订单簿
  4. `clob_balance` - 检查余额
  5. `clob_create_order` / `clob_market_order` - 下单

## 测试

### 运行所有测试
```bash
pytest
```

### 运行特定模块测试
```bash
pytest tests/test_security.py -v
pytest tests/test_retry.py -v
```

### 生成覆盖率报告
```bash
pytest --cov=src/openclaw_polymarket_skill --cov-report=html
```

覆盖率报告将生成在 `htmlcov/index.html`

### 🆕 测试覆盖率目标
- **Security 模块**: > 90%
- **Retry 模块**: > 95%
- **Executor 模块**: > 85%
- **整体覆盖率**: > 70%

## 🔒 安全最佳实践

### 1. 私钥管理
```bash
# ❌ 不要在代码中硬编码私钥
private_key = "0x1234..."

# ✅ 使用环境变量
export POLYMARKET_PRIVATE_KEY=0x...

# ✅ 使用密钥管理服务
# AWS Secrets Manager, HashiCorp Vault, etc.
```

### 2. 验证私钥格式
v0.2.0 引入了严格的私钥验证：
- 必须是 `0x` + 64位十六进制字符
- 自动检测 9 种常见 placeholder 模式
- 防止使用测试密钥进行真实交易

### 3. 日志安全
```python
# ✅ 所有敏感参数自动脱敏
# 支持两种格式:
# --private-key 0xABCD1234 → --private-key ***REDACTED***
# --private-key=0xABCD1234 → --private-key=***REDACTED***
```

### 4. 交易门控
```bash
# 多层安全检查
export OPENCLAW_PM_ALLOW_TRADING=false  # 全局开关
export OPENCLAW_PM_DRY_RUN=true         # Dry-run 模式
export OPENCLAW_PM_MAX_AUTO_AMOUNT=10   # 金额限制
```

## 🐛 错误处理

### 重试策略（v0.2.0 新增）

只读操作支持自动重试：
```python
from openclaw_polymarket_skill.retry import async_retry, RetryConfig

@async_retry(RetryConfig(max_attempts=3, initial_delay=1.0))
async def fetch_markets():
    # 网络错误会自动重试
    # 业务逻辑错误不会重试
    ...
```

**可重试错误**:
- `asyncio.TimeoutError`
- `ConnectionError`
- `OSError`

**不可重试错误**:
- 业务逻辑错误
- 参数验证错误
- 所有写操作（避免重复下单）

### 超时处理

v0.2.0 改进：
- 超时后显式终止子进程
- 准确的执行时长统计
- 完整的错误上下文

## 📚 文档

- **[ITERATION_DEV_DOC.md](ITERATION_DEV_DOC.md)**: v0.2.0 迭代开发文档
- **[CHANGELOG.md](CHANGELOG.md)**: 完整变更历史
- **[docs/OPENCLAW_INTEGRATION.md](docs/OPENCLAW_INTEGRATION.md)**: OpenClaw 对接说明
- **[docs/DEPLOYMENT.md](docs/DEPLOYMENT.md)**: 部署文档
- **[docs/OPERATIONS.md](docs/OPERATIONS.md)**: 运维手册

## ⚠️ 注意事项

### 通用
- JSON 模式错误通常在 stdout，而不是 stderr
- 非幂等写操作超时后不要自动重试，应先查询 `clob_orders` / `clob_trades`
- 请勿在日志里输出原始私钥（v0.2.0 已自动脱敏）

### v0.2.0 特别说明
- 🔒 私钥验证已加强，旧的弱密钥可能被拒绝
- 🔄 只读操作默认启用重试，写操作不会自动重试
- 📊 日志格式可配置，建议生产环境使用 JSON 格式

## 🚀 从 v0.1.0 升级到 v0.2.0

### 1. 更新代码
```bash
git pull origin main
git checkout v0.2.0
```

### 2. 安装新依赖
```bash
pip install -e ".[dev]"
```

### 3. 运行测试
```bash
pytest
```

### 4. 检查私钥格式
确保私钥符合新的验证标准（0x + 64位十六进制）

### 5. 配置日志（可选）
```bash
export OPENCLAW_PM_LOG_FORMAT=json
export OPENCLAW_PM_LOG_LEVEL=INFO
```

## 🤝 贡献

欢迎提交 Pull Request！

### 开发流程
1. Fork 本仓库
2. 创建功能分支 (`git checkout -b feature/amazing-feature`)
3. 提交更改 (`git commit -m 'Add amazing feature'`)
4. 推送到分支 (`git push origin feature/amazing-feature`)
5. 创建 Pull Request

### 代码质量要求
- ✅ 所有测试通过 (`pytest`)
- ✅ 覆盖率不降低 (`pytest --cov`)
- ✅ 符合 PEP 8 规范
- ✅ 添加必要的文档

## 📄 License

MIT License - 详见 [LICENSE](LICENSE) 文件

## 🔗 相关链接

- [Polymarket 官网](https://polymarket.com/)
- [Polymarket CLI](https://github.com/Polymarket/polymarket-cli)
- [OpenClaw 框架](https://github.com/openclaw)
- [问题反馈](https://github.com/DESONGs/claw-polymarket/issues)

---

**Made with ❤️ by OpenClaw Skill Team**
