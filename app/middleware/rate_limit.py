"""Sliding-window rate limiter middleware for the /chat endpoint (SEC-5, FR-10.10).

Uses a simple in-memory sliding window counter.  Only applies to POST /chat;
all other endpoints are unaffected.
"""

from __future__ import annotations

import time
from collections import deque

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import JSONResponse, Response


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Global sliding-window rate limiter for the /chat endpoint."""

    def __init__(self, app, max_requests: int = 60, window_seconds: int = 60) -> None:
        super().__init__(app)
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._timestamps: deque[float] = deque()

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        # Only rate-limit POST /chat
        if request.method == "POST" and request.url.path == "/chat":
            now = time.time()
            cutoff = now - self.window_seconds

            # Remove expired timestamps
            while self._timestamps and self._timestamps[0] < cutoff:
                self._timestamps.popleft()

            if len(self._timestamps) >= self.max_requests:
                return JSONResponse(
                    status_code=429,
                    content={"detail": "Too many requests. Please slow down."},
                )

            self._timestamps.append(now)

        return await call_next(request)
