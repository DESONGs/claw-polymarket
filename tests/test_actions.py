from openclaw_polymarket_skill.actions import ACTION_REGISTRY


def test_registry_contains_core_actions() -> None:
    required = {
        "markets_search",
        "markets_get",
        "clob_book",
        "clob_balance",
        "clob_create_order",
        "clob_market_order",
        "clob_cancel",
    }
    assert required.issubset(ACTION_REGISTRY.keys())


def test_markets_search_builder() -> None:
    args = ACTION_REGISTRY["markets_search"].builder({"query": "bitcoin", "limit": 5})
    assert args == ["markets", "search", "bitcoin", "--limit", "5"]


def test_clob_create_order_builder_defaults() -> None:
    args = ACTION_REGISTRY["clob_create_order"].builder(
        {"token": "123", "side": "buy", "price": "0.45", "size": "10"}
    )
    assert args == [
        "clob",
        "create-order",
        "--token",
        "123",
        "--side",
        "buy",
        "--price",
        "0.45",
        "--size",
        "10",
        "--order-type",
        "GTC",
    ]
