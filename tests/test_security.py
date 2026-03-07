"""
Security 模块测试
"""
import pytest
from decimal import Decimal

from openclaw_polymarket_skill.security import (
    estimate_amount,
    is_placeholder_key,
    is_valid_private_key,
    sanitize_cmd
)
from openclaw_polymarket_skill.settings import SkillSettings


class TestSanitizeCmd:
    """命令脱敏测试"""

    def test_sanitize_cmd_masks_private_key(self) -> None:
        """测试 --flag value 格式的私钥脱敏"""
        command = ["polymarket", "--private-key", "0xsecret", "clob", "orders"]
        assert sanitize_cmd(command) == ["polymarket", "--private-key", "***REDACTED***", "clob", "orders"]

    def test_sanitize_flag_equals_format(self) -> None:
        """测试 --flag=value 格式的脱敏"""
        cmd = ["polymarket", "--private-key=0xABCD1234"]
        result = sanitize_cmd(cmd)
        assert "0xABCD1234" not in " ".join(result)
        assert "--private-key=***REDACTED***" in result

    def test_sanitize_multiple_flags(self) -> None:
        """测试多个敏感参数"""
        cmd = [
            "polymarket",
            "--private-key", "key123",
            "--api-key=token456",
            "--secret", "secret789"
        ]
        result = sanitize_cmd(cmd)
        assert "key123" not in " ".join(result)
        assert "token456" not in " ".join(result)
        assert "secret789" not in " ".join(result)

    def test_no_sanitization_needed(self) -> None:
        """测试无需脱敏的命令"""
        cmd = ["polymarket", "markets", "search", "--limit", "10"]
        result = sanitize_cmd(cmd)
        assert result == cmd

    def test_sanitize_api_key(self) -> None:
        """测试 API key 脱敏"""
        cmd = ["polymarket", "--api-key=my-secret-token"]
        result = sanitize_cmd(cmd)
        assert "my-secret-token" not in " ".join(result)

    def test_sanitize_password(self) -> None:
        """测试密码脱敏"""
        cmd = ["polymarket", "--password", "mypassword123"]
        result = sanitize_cmd(cmd)
        assert "mypassword123" not in " ".join(result)


class TestPrivateKeyValidation:
    """私钥验证测试"""

    def test_valid_key(self) -> None:
        """测试有效私钥"""
        valid_key = "0x" + "a" * 64
        assert is_valid_private_key(valid_key) is True

    def test_invalid_length_short(self) -> None:
        """测试长度不足的密钥"""
        short_key = "0x" + "a" * 32
        assert is_valid_private_key(short_key) is False

    def test_missing_prefix(self) -> None:
        """测试缺少 0x 前缀"""
        no_prefix = "a" * 64
        assert is_valid_private_key(no_prefix) is False

    def test_invalid_characters(self) -> None:
        """测试非十六进制字符"""
        invalid = "0x" + "z" * 64
        assert is_valid_private_key(invalid) is False

    @pytest.mark.parametrize("placeholder", [
        "0x" + "0" * 64,
        "0x" + "f" * 64,
        "__PLACEHOLDER__",
        "YOUR_PRIVATE_KEY",
    ])
    def test_placeholder_detection(self, placeholder: str) -> None:
        """测试 placeholder 检测"""
        assert is_valid_private_key(placeholder) is False

    def test_none_value(self) -> None:
        """测试 None 值"""
        assert is_valid_private_key(None) is False

    def test_empty_string(self) -> None:
        """测试空字符串"""
        assert is_valid_private_key("") is False

    def test_valid_mixed_case_hex(self) -> None:
        """测试混合大小写十六进制私钥"""
        key = "0x" + "AbCdEf0123456789" * 4
        assert is_valid_private_key(key) is True


class TestIsPlaceholderKey:
    """is_placeholder_key 函数测试（兼容性）"""

    def test_placeholder_key_detected(self) -> None:
        """测试 placeholder 检测"""
        settings = SkillSettings()
        assert is_placeholder_key("__PLACEHOLDER__", settings) is True

    def test_real_key_not_placeholder(self) -> None:
        """测试真实密钥不是 placeholder"""
        settings = SkillSettings()
        key = "0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcd"
        assert is_placeholder_key(key, settings) is False

    def test_none_key(self) -> None:
        """测试 None 值"""
        settings = SkillSettings()
        assert is_placeholder_key(None, settings) is True

    def test_short_key_is_placeholder(self) -> None:
        """测试短密钥被识别为 placeholder"""
        settings = SkillSettings()
        short_key = "0x" + "a" * 32
        assert is_placeholder_key(short_key, settings) is True


class TestEstimateAmount:
    """金额估算测试"""

    def test_estimate_create_order_amount(self) -> None:
        """测试限价单金额估算"""
        amount = estimate_amount("clob_create_order", {"price": "0.5", "size": "10"})
        assert amount == Decimal("5")

    def test_estimate_market_order_buy_amount(self) -> None:
        """测试市价买单金额估算"""
        amount = estimate_amount("clob_market_order", {"side": "buy", "amount": "12.5"})
        assert amount == Decimal("12.5")
