from decimal import Decimal

from openclaw_polymarket_skill.security import estimate_amount, is_placeholder_key, sanitize_cmd
from openclaw_polymarket_skill.settings import SkillSettings


def test_sanitize_cmd_masks_private_key() -> None:
    command = ["polymarket", "--private-key", "0xsecret", "clob", "orders"]
    assert sanitize_cmd(command) == ["polymarket", "--private-key", "***REDACTED***", "clob", "orders"]


def test_placeholder_key_detected() -> None:
    settings = SkillSettings()
    assert is_placeholder_key("__PLACEHOLDER__", settings) is True


def test_real_key_not_placeholder() -> None:
    settings = SkillSettings()
    key = "0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcd"
    assert is_placeholder_key(key, settings) is False


def test_estimate_create_order_amount() -> None:
    amount = estimate_amount("clob_create_order", {"price": "0.5", "size": "10"})
    assert amount == Decimal("5")


def test_estimate_market_order_buy_amount() -> None:
    amount = estimate_amount("clob_market_order", {"side": "buy", "amount": "12.5"})
    assert amount == Decimal("12.5")
