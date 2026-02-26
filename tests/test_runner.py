import asyncio

from openclaw_polymarket_skill.executor import CommandResult
from openclaw_polymarket_skill.runner import PolymarketSkillRunner
from openclaw_polymarket_skill.settings import SkillSettings


class FakeExecutor:
    def __init__(self, result: CommandResult) -> None:
        self._result = result

    async def run(self, *args, **kwargs):  # type: ignore[no-untyped-def]
        return self._result

    async def check_cli_version(self):  # type: ignore[no-untyped-def]
        return True, "0.1.4"


class FakeExecutorVersionMismatch(FakeExecutor):
    async def check_cli_version(self):  # type: ignore[no-untyped-def]
        return False, "CLI 版本不匹配"


def test_unknown_action() -> None:
    runner = PolymarketSkillRunner(settings=SkillSettings(enforce_cli_version=False))
    result = asyncio.run(runner.execute("not_exists", {}))
    assert result["ok"] is False
    assert result["error"]["type"] == "UnknownAction"


def test_missing_required_param() -> None:
    runner = PolymarketSkillRunner(settings=SkillSettings(enforce_cli_version=False))
    result = asyncio.run(runner.execute("markets_search", {}))
    assert result["ok"] is False
    assert result["error"]["type"] == "ValidationError"


def test_write_blocked_when_trading_disabled() -> None:
    settings = SkillSettings(allow_trading=False, dry_run=False, enforce_cli_version=False)
    runner = PolymarketSkillRunner(settings=settings)
    result = asyncio.run(
        runner.execute(
            "clob_create_order",
            {"token": "123", "side": "buy", "price": "0.2", "size": "10"},
            {"private_key": "0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcd"},
        )
    )
    assert result["ok"] is False
    assert result["error"]["type"] == "TradingDisabledError"


def test_write_dry_run() -> None:
    settings = SkillSettings(allow_trading=True, dry_run=True, enforce_cli_version=False)
    runner = PolymarketSkillRunner(settings=settings)
    result = asyncio.run(
        runner.execute(
            "clob_create_order",
            {"token": "123", "side": "buy", "price": "0.2", "size": "10"},
            {"private_key": "0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcd"},
        )
    )
    assert result["ok"] is True
    assert result.get("dry_run") is True


def test_write_timeout_not_retryable() -> None:
    settings = SkillSettings(allow_trading=True, dry_run=False, enforce_cli_version=False)
    runner = PolymarketSkillRunner(settings=settings)
    runner.executor = FakeExecutor(
        CommandResult(
            ok=False,
            data=None,
            error={"type": "TimeoutError", "message": "timeout", "retryable": True},
            meta={"duration_ms": 100, "cmd_sanitized": ["polymarket"], "exit_code": 124},
        )
    )
    result = asyncio.run(
        runner.execute(
            "clob_create_order",
            {"token": "123", "side": "buy", "price": "0.2", "size": "10"},
            {"private_key": "0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcd"},
        )
    )
    assert result["ok"] is False
    assert result["error"]["type"] == "TimeoutError"
    assert result["error"]["retryable"] is False


def test_cli_version_mismatch_block_execute() -> None:
    runner = PolymarketSkillRunner(settings=SkillSettings())
    runner.executor = FakeExecutorVersionMismatch(
        CommandResult(ok=True, data={"ok": True}, error=None, meta={"duration_ms": 1, "cmd_sanitized": []})
    )
    result = asyncio.run(runner.execute("markets_search", {"query": "btc"}))
    assert result["ok"] is False
    assert result["error"]["type"] == "CliVersionMismatch"
