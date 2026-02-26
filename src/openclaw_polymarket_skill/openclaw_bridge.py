from __future__ import annotations

import asyncio
import json
from typing import Any

from .actions import ACTION_REGISTRY
from .runner import PolymarketSkillRunner


def _error_response(request_id: str | int | None, code: str, message: str) -> dict[str, Any]:
    return {
        "id": request_id,
        "ok": False,
        "error": {
            "code": code,
            "message": message,
        },
    }


async def handle_request(runner: PolymarketSkillRunner, request: dict[str, Any]) -> dict[str, Any]:
    request_id = request.get("id")
    method = request.get("method", "execute")

    if method == "list_actions":
        actions = [
            {
                "name": spec.name,
                "category": spec.category.value,
                "required_params": list(spec.required_params),
            }
            for spec in ACTION_REGISTRY.values()
        ]
        return {"id": request_id, "ok": True, "result": {"actions": actions}}

    if method == "healthcheck":
        result = await runner.healthcheck()
        return {"id": request_id, "ok": bool(result.get("ok")), "result": result}

    if method != "execute":
        return _error_response(request_id, "UnsupportedMethod", f"不支持的方法: {method}")

    action = request.get("action")
    if not action:
        return _error_response(request_id, "ValidationError", "缺少 action 字段")

    params = request.get("params")
    context = request.get("context")
    if params is not None and not isinstance(params, dict):
        return _error_response(request_id, "ValidationError", "params 必须是 JSON 对象")
    if context is not None and not isinstance(context, dict):
        return _error_response(request_id, "ValidationError", "context 必须是 JSON 对象")

    result = await runner.execute(action=str(action), params=params or {}, context=context or {})
    return {"id": request_id, "ok": bool(result.get("ok")), "result": result}


async def serve_stdio() -> None:
    runner = PolymarketSkillRunner()
    loop = asyncio.get_event_loop()
    while True:
        line = await loop.run_in_executor(None, input)
        if line is None:
            break
        payload = line.strip()
        if not payload:
            continue

        try:
            request = json.loads(payload)
        except json.JSONDecodeError:
            print(
                json.dumps(
                    _error_response(None, "InvalidJson", "输入不是合法 JSON"),
                    ensure_ascii=False,
                ),
                flush=True,
            )
            continue

        if not isinstance(request, dict):
            print(
                json.dumps(
                    _error_response(None, "ValidationError", "请求必须是 JSON 对象"),
                    ensure_ascii=False,
                ),
                flush=True,
            )
            continue

        response = await handle_request(runner, request)
        print(json.dumps(response, ensure_ascii=False), flush=True)
