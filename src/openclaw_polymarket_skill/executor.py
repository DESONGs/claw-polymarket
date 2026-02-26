from __future__ import annotations

import asyncio
import json
import os
from dataclasses import dataclass
from typing import Any

from .errors import classify_error
from .security import sanitize_cmd
from .settings import SkillSettings


@dataclass(frozen=True)
class CommandResult:
    ok: bool
    data: Any | None
    error: dict[str, Any] | None
    meta: dict[str, Any]


class PolymarketExecutor:
    def __init__(self, settings: SkillSettings) -> None:
        self.settings = settings

    async def check_cli_version(self) -> tuple[bool, str]:
        command = [self.settings.polymarket_bin, "--version"]
        try:
            process = await asyncio.create_subprocess_exec(
                *command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, _ = await asyncio.wait_for(process.communicate(), timeout=5)
        except (FileNotFoundError, asyncio.TimeoutError):
            return False, "无法执行 polymarket --version，请确认二进制已安装并在 PATH 中"

        line = stdout.decode("utf-8", errors="ignore").strip()
        if not line:
            return False, "polymarket --version 输出为空"
        version = line.split()[-1]
        if version != self.settings.cli_version:
            return (
                False,
                f"CLI 版本不匹配，期望 {self.settings.cli_version}，实际 {version}",
            )
        return True, version

    async def run(
        self,
        cli_args: list[str],
        timeout_seconds: int,
        env_overrides: dict[str, str | None] | None = None,
    ) -> CommandResult:
        command = [self.settings.polymarket_bin, "-o", "json", *cli_args]
        meta = {
            "cmd_sanitized": sanitize_cmd(command),
            "duration_ms": 0,
        }

        environment = os.environ.copy()
        if env_overrides:
            for key, value in env_overrides.items():
                if value is not None:
                    environment[key] = value

        started = asyncio.get_event_loop().time()
        try:
            process = await asyncio.create_subprocess_exec(
                *command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=environment,
            )
            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=timeout_seconds,
            )
        except FileNotFoundError:
            return CommandResult(
                ok=False,
                data=None,
                error={
                    "type": "BinaryNotFound",
                    "message": f"找不到命令: {self.settings.polymarket_bin}",
                    "retryable": False,
                },
                meta=meta,
            )
        except asyncio.TimeoutError:
            meta["duration_ms"] = int((asyncio.get_event_loop().time() - started) * 1000)
            return CommandResult(
                ok=False,
                data=None,
                error={
                    "type": "TimeoutError",
                    "message": f"命令执行超时（{timeout_seconds}s）",
                    "retryable": True,
                },
                meta=meta,
            )

        meta["duration_ms"] = int((asyncio.get_event_loop().time() - started) * 1000)
        meta["exit_code"] = process.returncode

        raw_stdout = stdout.decode("utf-8", errors="ignore").strip()
        raw_stderr = stderr.decode("utf-8", errors="ignore").strip()

        parsed: Any | None
        try:
            parsed = json.loads(raw_stdout) if raw_stdout else None
        except json.JSONDecodeError:
            parsed = None

        if process.returncode == 0:
            return CommandResult(ok=True, data=parsed if parsed is not None else raw_stdout, error=None, meta=meta)

        if isinstance(parsed, dict) and "error" in parsed:
            message = str(parsed["error"])
            cli_error = parsed
        else:
            message = raw_stderr or raw_stdout or f"命令执行失败，退出码 {process.returncode}"
            cli_error = None

        error_info = classify_error(message)
        return CommandResult(
            ok=False,
            data=None,
            error={
                "type": error_info.type,
                "message": message,
                "retryable": error_info.retryable,
                "cli_error": cli_error,
            },
            meta=meta,
        )
