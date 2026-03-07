# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.3.1] - 2026-03-07

### Fixed
- 🐛 **修复**: `validators.py` 中 `TOKEN_ID_RE` 正则表达式仅允许纯数字，导致 `markets_search` 返回的十六进制 `clobTokenIds`（`0x...` 格式）无法传入 `clob_midpoint` / `clob_spread` / `clob_book` 等 CLOB action
  - 修复前：`TOKEN_ID_RE = re.compile(r"^[0-9]{1,100}$")`
  - 修复后：`TOKEN_ID_RE = re.compile(r"^([0-9]{1,100}|0x[0-9a-fA-F]{1,64})$")`
  - 与 `polymarket-cli` 底层 `U256::from_str()` 实际行为对齐（同时支持十进制和十六进制）

## [0.3.0] - 2026-03-06

### Added
- ✨ **新功能**: 端到端市场分析工作流 (`analyze` 子命令)
  - 一键编排多个现有 action，采集完整市场数据（盘口/价差/委托簿/历史价格）
  - 调用 Claude API 进行 AI 深度分析，支持自定义分析提示词
  - 输出结构化 JSON 数据 + Markdown 分析报告

- ✨ **新功能**: `analyze_models.py` — 分析工作流专用数据类
  - `TokenData`: 单个 token 的行情数据
  - `MarketSnapshot`: 查询结果快照（含精简摘要方法 `to_summary_dict()`）
  - `AnalysisResult`: 完整分析结果（含 `to_dict()` 序列化）

- ✨ **新功能**: `market_collector.py` — 并行市场数据采集
  - `asyncio.gather` 并行采集每个 market 的 midpoint/spread/book/history
  - 单 token 失败记录到 `fetch_errors`，不中断整体流程
  - events_list 失败不阻塞主流程

- ✨ **新功能**: `claude_client.py` — Claude API 封装
  - 固定 system prompt，设定专业预测市场分析师角色
  - 要求严格返回 `structured` + `report_markdown` 两个顶层键
  - 三级降级策略：直接解析 → 提取 JSON 块 → 原始文本

- ✨ **新功能**: `report_builder.py` — 多格式输出构建
  - 支持 `json` / `markdown` / `both` 三种输出格式
  - 无 `report_markdown` 时自动生成 fallback Markdown 报告

- 🔧 **配置**: `settings.py` 新增 3 个 Claude 字段（带默认值，向后兼容）
  - `anthropic_api_key` — 读取 `ANTHROPIC_API_KEY`
  - `claude_timeout_seconds` — 读取 `OPENCLAW_CLAUDE_TIMEOUT`（默认 60）
  - `claude_max_tokens` — 读取 `OPENCLAW_CLAUDE_MAX_TOKENS`（默认 4096）

- 📦 **依赖**: 添加 `anthropic>=0.37.0`

- 📄 **模板**: `.env.openclaw.template` 补充 Claude 相关环境变量说明

### Usage

```bash
# 基本用法
openclaw-polymarket-skill analyze \
  --query "bitcoin price prediction" \
  --analysis-prompt "从做市商视角分析买卖价差和流动性风险" \
  --market-limit 5 \
  --output both

# 无 API key 时退出码为 2
unset ANTHROPIC_API_KEY && openclaw-polymarket-skill analyze --query "test" --analysis-prompt "test"
echo $?  # 输出 2
```

## [0.2.0] - 2026-03-02

### Added
- ✨ **新功能**: 结构化日志系统 (`logging_config.py`)
  - 支持 JSON 格式的结构化日志
  - 支持纯文本格式日志
  - 可配置的日志级别

- ✨ **新功能**: 智能重试机制 (`retry.py`)
  - 指数退避算法
  - 可配置的重试策略
  - 自动识别可重试/不可重试错误
  - 支持抖动(jitter)避免雷鸣效应

- 🧪 **测试**: 完整的单元测试套件
  - Security 模块测试覆盖率 > 90%
  - Retry 模块测试覆盖率 > 95%
  - 添加 pytest 配置和 fixtures

- 📚 **文档**: 迭代开发文档 (`ITERATION_DEV_DOC.md`)
  - 详细的技术架构说明
  - 代码改进方案
  - 测试策略
  - 验收标准

### Changed
- 🔒 **安全**: 增强命令脱敏机制
  - 修复 `--flag=value` 格式无法脱敏的漏洞
  - 扩展敏感参数列表(支持 `--api-key`, `--secret`, `--password`, `--token`)
  - 改进的脱敏逻辑

- 🔒 **安全**: 增强私钥验证
  - 添加 `is_valid_private_key()` 函数
  - 严格的格式验证(0x + 64位十六进制)
  - 扩展的 placeholder 模式检测(9种模式)
  - 使用正则表达式进行模式匹配

- 🛠️ **改进**: 完善 executor 错误处理
  - 统一的时间追踪机制
  - 超时后显式终止子进程
  - 空响应检测
  - 完整保留 stdout/stderr 信息
  - 新增 `_handle_success()` 和 `_handle_failure()` 方法
  - 更详细的错误元数据

- 📦 **依赖**: 更新开发依赖
  - `pytest-asyncio>=0.23.0`
  - `pytest-cov>=4.1.0`
  - `pytest-mock>=3.12.0`

### Fixed
- 🐛 修复超时后 `duration_ms` 计算不一致的问题
- 🐛 修复 JSON 解析失败时丢失 stderr 的问题
- 🐛 修复空响应未被正确检测的问题
- 🐛 修复进程超时后未显式终止的问题

### Security
- 🔐 修复高危安全漏洞: 命令参数脱敏不完整
- 🔐 增强私钥验证强度，防止弱密钥使用
- 🔐 扩展 placeholder 检测覆盖范围

## [0.1.0] - 2024-XX-XX

### Added
- 初始版本发布
- 支持 Polymarket CLI 基本操作
- 市场查询功能
- CLOB 交易功能
- 基础安全机制
- 命令执行器
- 参数验证

[0.3.1]: https://github.com/DESONGs/claw-polymarket/compare/v0.3.0...v0.3.1
[0.3.0]: https://github.com/DESONGs/claw-polymarket/compare/v0.2.0...v0.3.0
[0.2.0]: https://github.com/DESONGs/claw-polymarket/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/DESONGs/claw-polymarket/releases/tag/v0.1.0
