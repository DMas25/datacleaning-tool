from __future__ import annotations

import asyncio
import json

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from starlette.types import ASGIApp

_TIMEOUT_SECONDS = 30

_TIMEOUT_BODY = json.dumps({
    "detail": (
        f"Request exceeded the {_TIMEOUT_SECONDS}s time limit. "
        "If processing a large dataset, split it into batches of 5,000 rows or fewer."
    )
})


class TimeoutMiddleware(BaseHTTPMiddleware):
    """
    Kills cleaning requests that stall beyond the time limit.
    Prevents one oversized or misbehaving request from blocking all subsequent workers.
    Returns HTTP 504 with a JSON body matching the standard error schema.
    """

    def __init__(self, app: ASGIApp, timeout: int = _TIMEOUT_SECONDS) -> None:
        super().__init__(app)
        self.timeout = timeout

    async def dispatch(self, request: Request, call_next) -> Response:
        try:
            return await asyncio.wait_for(call_next(request), timeout=self.timeout)
        except asyncio.TimeoutError:
            return Response(
                content=_TIMEOUT_BODY,
                status_code=504,
                media_type="application/json",
            )
