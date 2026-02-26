from __future__ import annotations

import os
from decimal import Decimal
from typing import Any

from .actions import ACTION_REGISTRY
from .executor import PolymarketExecutor
from .locks import WalletLockManager
from .security import estimate_amount, is_placeholder_key
from .settings import SkillSettings
from .validators import validate_param, validate_presence


class PolymarketSkillRunner:
    def __init__(self, settings: SkillSettings | None = None) -> None:
        self.settings = settings or SkillSettings.from_env()
        self.executor = PolymarketExecutor(self.settings)
        self.lock_manager = WalletLockManager()
        self._version_checked = False

    async def healthcheck(self) -> dict[str, Any]:
        ok, message = await self.executor.check_cli_version()
        return {
            "ok": ok,
            "version": message if ok else None,
            "error": None if ok else message,
        }

    async def execute(
        self,
        action: str,
        params: dict[str, Any] | None = None,
        context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        payload = params or {}
        runtime = context or {}

        if self.settings.enforce_cli_version and not self._version_checked:
            ok, message = await self.executor.check_cli_version()
            if not ok:
                return self._error(
                    action,
                    "CliVersionMismatch",
                    message,
                    retryable=False,
                )
            self._version_checked = True

        if action not in ACTION_REGISTRY:
            return self._error(
                action,
                "UnknownAction",
                f"未知 action: {action}",
                retryable=False,
            )

        spec = ACTION_REGISTRY[action]
        missing_error = validate_presence(payload, spec.required_params)
        if missing_error:
            return self._error(action, "ValidationError", missing_error, retryable=False)

        for key, value in payload.items():
            validation_error = validate_param(key, value)
            if validation_error:
                return self._error(action, "ValidationError", validation_error, retryable=False)

        args = spec.builder(payload)

        # 写操作门控
        if spec.is_write:
            if not self.settings.allow_trading:
                return self._error(
                    action,
                    "TradingDisabledError",
                    "交易功能未启用，请设置 OPENCLAW_PM_ALLOW_TRADING=true",
                    retryable=False,
                )

            private_key = runtime.get("private_key")
            if private_key is None:
                private_key = runtime.get("POLYMARKET_PRIVATE_KEY")
            if private_key is None:
                private_key = os.getenv("POLYMARKET_PRIVATE_KEY")

            if is_placeholder_key(private_key, self.settings):
                return self._error(
                    action,
                    "PlaceholderKeyError",
                    "当前私钥为占位符，拒绝真实交易",
                    retryable=False,
                )

            if self.settings.dry_run:
                return {
                    "ok": True,
                    "action": action,
                    "dry_run": True,
                    "data": {
                        "would_execute": [self.settings.polymarket_bin, "-o", "json", *args],
                        "warnings": [
                            "当前为 dry-run 模式，未真实执行交易",
                        ],
                    },
                    "meta": {"action": action, "duration_ms": 0},
                }

            expected_amount = estimate_amount(action, payload)
            if expected_amount is not None and expected_amount > Decimal(str(self.settings.max_auto_amount)):
                return self._error(
                    action,
                    "HumanApprovalRequired",
                    (
                        f"预估金额 ${expected_amount:.2f} 超过自动执行阈值 "
                        f"${self.settings.max_auto_amount:.2f}，需要人工确认"
                    ),
                    retryable=False,
                    extra={"approval_context": {"estimated_amount": str(expected_amount)}},
                )

        timeout = self.settings.write_timeout_seconds if spec.is_write else self.settings.read_timeout_seconds
        env_overrides = self._build_env_overrides(runtime)

        async def _do_execute() -> dict[str, Any]:
            command_result = await self.executor.run(args, timeout_seconds=timeout, env_overrides=env_overrides)
            if command_result.ok:
                return {
                    "ok": True,
                    "action": action,
                    "data": command_result.data,
                    "meta": {"action": action, **command_result.meta},
                }
            return {
                "ok": False,
                "action": action,
                "error": command_result.error,
                "meta": {"action": action, **command_result.meta},
            }

        if spec.is_write:
            wallet_id = str(runtime.get("wallet_id") or runtime.get("address") or "default-wallet")
            result = await self.lock_manager.run_with_wallet_lock(wallet_id, _do_execute)
            return self._fix_timeout_retryable(result, is_write=True)

        result = await _do_execute()
        return self._fix_timeout_retryable(result, is_write=False)

    def _build_env_overrides(self, runtime: dict[str, Any]) -> dict[str, str | None]:
        private_key = runtime.get("private_key") or runtime.get("POLYMARKET_PRIVATE_KEY")
        signature_type = runtime.get("signature_type") or runtime.get("POLYMARKET_SIGNATURE_TYPE")
        return {
            "POLYMARKET_PRIVATE_KEY": str(private_key) if private_key is not None else None,
            "POLYMARKET_SIGNATURE_TYPE": str(signature_type) if signature_type is not None else self.settings.default_signature_type,
        }

    def _fix_timeout_retryable(self, result: dict[str, Any], is_write: bool) -> dict[str, Any]:
        if result.get("ok") is False and result.get("error", {}).get("type") == "TimeoutError":
            result["error"]["retryable"] = not is_write
            if is_write:
                result["error"]["message"] = (
                    f"{result['error']['message']}。写操作超时后请先查询 clob_orders / clob_trades，"
                    "不要直接重试下单。"
                )
        return result

    def _error(
        self,
        action: str,
        error_type: str,
        message: str,
        retryable: bool,
        extra: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "ok": False,
            "action": action,
            "error": {
                "type": error_type,
                "message": message,
                "retryable": retryable,
            },
            "meta": {"action": action, "duration_ms": 0},
        }
        if extra:
            payload["error"].update(extra)
        return payload
