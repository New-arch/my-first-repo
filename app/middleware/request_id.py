"""Middleware that generates a unique X-Request-Id for every request."""

from __future__ import annotations

import uuid

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response


class RequestIdMiddleware(BaseHTTPMiddleware):
    """Attach a UUID ``X-Request-Id`` header to every response.

    If the incoming request already carries the header it is preserved;
    otherwise a new UUID4 is generated.  The id is also stored in
    ``request.state.request_id`` so downstream code can reference it.
    """

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        request_id = request.headers.get("X-Request-Id") or str(uuid.uuid4())
        request.state.request_id = request_id

        response = await call_next(request)
        response.headers["X-Request-Id"] = request_id
        return response
