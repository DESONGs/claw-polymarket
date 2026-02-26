from __future__ import annotations

import asyncio
from collections import defaultdict
from typing import Any, Awaitable, Callable


class WalletLockManager:
    def __init__(self) -> None:
        self._locks: defaultdict[str, asyncio.Lock] = defaultdict(asyncio.Lock)

    async def run_with_wallet_lock(
        self,
        wallet_id: str,
        task_factory: Callable[[], Awaitable[dict[str, Any]]],
    ) -> dict[str, Any]:
        lock = self._locks[wallet_id]
        async with lock:
            return await task_factory()
