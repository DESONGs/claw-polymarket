# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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

[0.2.0]: https://github.com/DESONGs/claw-polymarket/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/DESONGs/claw-polymarket/releases/tag/v0.1.0
