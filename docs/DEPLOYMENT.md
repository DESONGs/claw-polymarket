# 部署文档（OpenClaw Polymarket Skill）

## 1. 目标

将 `openclaw-polymarket-skill` 部署到可被 OpenClaw 调用的运行环境，并以 `stdio bridge` 模式提供服务。

## 2. 前置条件

- Python 3.10+
- 已安装或可访问 `polymarket` CLI（二进制名 `polymarket`）
- 网络可访问 Polymarket API

## 3. 本机部署（推荐先做）

```bash
cd openclaw-polymarket-skill
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
cp openclaw/.env.openclaw.template openclaw/.env.openclaw
```

检查：

```bash
openclaw-polymarket-skill healthcheck
openclaw-polymarket-skill list-actions
```

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

启动服务：

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now openclaw-polymarket-skill
sudo systemctl status openclaw-polymarket-skill
```

## 5. OpenClaw 侧接入

1. 复制 `openclaw/openclaw-skill-config.template.json` 到 OpenClaw 的 skill 配置目录
2. 修改 command 为实际路径（如 `.venv/bin/openclaw-polymarket-skill`）
3. 修改 `cwd` 为部署目录
4. 重启 OpenClaw skill manager

## 6. 发布流程（建议）

1. 在测试环境验证：
   - `healthcheck` 成功
   - `markets_search` 成功
   - 交易动作在 dry-run 下返回预期
2. 灰度发布：
   - 先只读
   - 再放开交易并保留人工确认
3. 观测错误率和超时率后全量发布

## 7. 回滚方案

若新版本异常：

1. 回滚代码目录到上一个版本
2. `pip install -e .` 重新安装
3. 重启服务：`sudo systemctl restart openclaw-polymarket-skill`
4. 验证 `healthcheck` 和 `list-actions`
