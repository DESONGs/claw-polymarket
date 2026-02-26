from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class SkillSettings:
    polymarket_bin: str = "polymarket"
    default_signature_type: str = "proxy"
    placeholder_private_key: str = "__PLACEHOLDER__"
    allow_trading: bool = False
    dry_run: bool = True
    max_auto_amount: float = 10.0
    read_timeout_seconds: int = 15
    write_timeout_seconds: int = 60
    cli_version: str = "0.1.4"
    enforce_cli_version: bool = True

    @staticmethod
    def from_env() -> "SkillSettings":
        return SkillSettings(
            polymarket_bin=os.getenv("OPENCLAW_PM_BIN", "polymarket"),
            default_signature_type=os.getenv("POLYMARKET_SIGNATURE_TYPE", "proxy"),
            placeholder_private_key=os.getenv("OPENCLAW_PM_PLACEHOLDER_KEY", "__PLACEHOLDER__"),
            allow_trading=os.getenv("OPENCLAW_PM_ALLOW_TRADING", "false").lower() == "true",
            dry_run=os.getenv("OPENCLAW_PM_DRY_RUN", "true").lower() != "false",
            max_auto_amount=float(os.getenv("OPENCLAW_PM_MAX_AUTO_AMOUNT", "10")),
            read_timeout_seconds=int(os.getenv("OPENCLAW_PM_READ_TIMEOUT_SECONDS", "15")),
            write_timeout_seconds=int(os.getenv("OPENCLAW_PM_WRITE_TIMEOUT_SECONDS", "60")),
            cli_version=os.getenv("OPENCLAW_PM_CLI_VERSION", "0.1.4"),
            enforce_cli_version=os.getenv("OPENCLAW_PM_ENFORCE_VERSION", "true").lower() == "true",
        )
