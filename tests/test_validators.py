from openclaw_polymarket_skill.validators import validate_param


def test_token_validation() -> None:
    assert validate_param("token_id", "123456") is None
    assert validate_param("token_id", "abc") is not None


def test_price_validation() -> None:
    assert validate_param("price", "0.55") is None
    assert validate_param("price", "1.2") is not None
    assert validate_param("price", "-1") is not None


def test_limit_validation() -> None:
    assert validate_param("limit", 5) is None
    assert validate_param("limit", 0) is not None


def test_address_validation() -> None:
    assert validate_param("address", "0x0000000000000000000000000000000000000001") is None
    assert validate_param("address", "0x1234") is not None


def test_asset_type_validation() -> None:
    assert validate_param("asset_type", "collateral") is None
    assert validate_param("asset_type", "conditional") is None
    assert validate_param("asset_type", "unknown") is not None


def test_market_condition_validation() -> None:
    assert (
        validate_param(
            "market",
            "0x0000000000000000000000000000000000000000000000000000000000000001",
        )
        is None
    )
    assert validate_param("market", "not-a-condition-id") is not None
