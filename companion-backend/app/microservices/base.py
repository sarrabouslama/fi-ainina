import asyncio
import time
from dataclasses import dataclass

import httpx


@dataclass
class CircuitState:
    failures: int = 0
    opened_at: float | None = None


class AsyncServiceClient:
    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip('/')
        self._state = CircuitState()
        self._client = httpx.AsyncClient(base_url=self.base_url, timeout=8)

    async def _request(self, method: str, path: str, **kwargs):
        if self._state.opened_at and (time.time() - self._state.opened_at < 30):
            raise RuntimeError('Circuit breaker open')

        delay = 0.2
        last_exc = None
        for _ in range(3):
            try:
                response = await self._client.request(method, path, **kwargs)
                response.raise_for_status()
                self._state.failures = 0
                self._state.opened_at = None
                return response
            except Exception as exc:
                last_exc = exc
                self._state.failures += 1
                if self._state.failures >= 5:
                    self._state.opened_at = time.time()
                await asyncio.sleep(delay)
                delay *= 2

        raise RuntimeError('Upstream call failed') from last_exc

    async def close(self):
        await self._client.aclose()
