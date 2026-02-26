import asyncio

from openclaw_polymarket_skill.openclaw_bridge import handle_request


class FakeRunner:
    async def healthcheck(self):  # type: ignore[no-untyped-def]
        return {"ok": True, "version": "0.1.4", "error": None}

    async def execute(self, action, params=None, context=None):  # type: ignore[no-untyped-def]
        return {
            "ok": True,
            "action": action,
            "data": {"params": params or {}, "context": context or {}},
            "meta": {"duration_ms": 1},
        }


def test_bridge_healthcheck() -> None:
    response = asyncio.run(handle_request(FakeRunner(), {"id": "1", "method": "healthcheck"}))
    assert response["id"] == "1"
    assert response["ok"] is True
    assert response["result"]["ok"] is True


def test_bridge_execute() -> None:
    response = asyncio.run(
        handle_request(
            FakeRunner(),
            {
                "id": "2",
                "method": "execute",
                "action": "markets_search",
                "params": {"query": "btc"},
                "context": {"wallet_id": "u1"},
            },
        )
    )
    assert response["id"] == "2"
    assert response["ok"] is True
    assert response["result"]["action"] == "markets_search"


def test_bridge_invalid_method() -> None:
    response = asyncio.run(handle_request(FakeRunner(), {"id": "x", "method": "unknown"}))
    assert response["ok"] is False
    assert response["error"]["code"] == "UnsupportedMethod"
