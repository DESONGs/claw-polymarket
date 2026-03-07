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
        """
        执行 polymarket CLI 命令

        改进:
        1. 统一的时间追踪
        2. 超时后显式终止进程
        3. 完整保留 stdout/stderr
        4. 空响应检测
        """
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
        process = None

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

            # 计算执行时长
            meta["duration_ms"] = int((asyncio.get_event_loop().time() - started) * 1000)
            meta["exit_code"] = process.returncode

            # 解码输出
            raw_stdout = stdout.decode("utf-8", errors="ignore").strip()
            raw_stderr = stderr.decode("utf-8", errors="ignore").strip()

            # 成功情况下的处理
            if process.returncode == 0:
                return self._handle_success(raw_stdout, raw_stderr, meta)
            else:
                return self._handle_failure(raw_stdout, raw_stderr, process.returncode, meta)

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
            # 计算实际执行时长
            meta["duration_ms"] = int((asyncio.get_event_loop().time() - started) * 1000)
            meta["timed_out"] = True

            # 显式终止进程
            if process and process.returncode is None:
                try:
                    process.kill()
                    await process.wait()
                except Exception:
                    pass  # 进程可能已经终止

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

        except Exception as e:
            # 捕获其他异常
            meta["duration_ms"] = int((asyncio.get_event_loop().time() - started) * 1000)
            return CommandResult(
                ok=False,
                data=None,
                error={
                    "type": "ExecutionError",
                    "message": f"执行异常: {str(e)}",
                    "retryable": False,
                    "exception_type": type(e).__name__,
                },
                meta=meta,
            )

    def _handle_success(
        self,
        raw_stdout: str,
        raw_stderr: str,
        meta: dict[str, Any]
    ) -> CommandResult:
        """处理成功的命令执行"""
        # 检查空响应
        if not raw_stdout:
            meta["warning"] = "Exit code 0 but no output"
            if raw_stderr:
                meta["stderr"] = raw_stderr
            return CommandResult(
                ok=False,
                data=None,
                error={
                    "type": "EmptyResponse",
                    "message": "命令执行成功但无输出",
                    "retryable": False,
                },
                meta=meta,
            )

        # 尝试解析 JSON
        parsed: Any | None
        try:
            parsed = json.loads(raw_stdout)
            if raw_stderr:
                meta["stderr"] = raw_stderr
            return CommandResult(
                ok=True,
                data=parsed,
                error=None,
                meta=meta
            )
        except json.JSONDecodeError as e:
            # JSON 解析失败，但命令执行成功
            meta["warning"] = f"Non-JSON response: {str(e)}"
            meta["format"] = "raw_text"
            if raw_stderr:
                meta["stderr"] = raw_stderr
            return CommandResult(
                ok=True,
                data=raw_stdout,
                error=None,
                meta=meta
            )

    def _handle_failure(
        self,
        raw_stdout: str,
        raw_stderr: str,
        returncode: int,
        meta: dict[str, Any]
    ) -> CommandResult:
        """处理失败的命令执行"""
        # 尝试从 stdout 解析错误信息
        parsed: Any | None
        try:
            parsed = json.loads(raw_stdout) if raw_stdout else None
        except json.JSONDecodeError:
            parsed = None

        # 提取错误信息
        if isinstance(parsed, dict) and "error" in parsed:
            message = str(parsed["error"])
            cli_error = parsed
        else:
            message = raw_stderr or raw_stdout or f"命令执行失败，退出码 {returncode}"
            cli_error = None

        # 保留完整的输出信息
        if raw_stdout:
            meta["stdout"] = raw_stdout
        if raw_stderr:
            meta["stderr"] = raw_stderr

        # 分类错误
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
