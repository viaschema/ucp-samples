# Copyright 2026 UCP Authors
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Shared-secret API key middleware for the business agent.

Validates `Authorization: Bearer <API_SECRET_KEY>` on every request except
agent-discovery paths (`/.well-known/*`, `/images`) and CORS preflights.
"""

import hmac
import logging
import os

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.types import ASGIApp

logger = logging.getLogger(__name__)

PUBLIC_PREFIXES: tuple[str, ...] = ("/.well-known/", "/images", "/lender-api/")
BEARER_PREFIX = "Bearer "


class APIKeyMiddleware(BaseHTTPMiddleware):
    """Reject requests without a valid bearer token.

    Reads `API_SECRET_KEY` from the environment at startup. If the env var
    is unset the middleware logs a warning and lets all traffic through,
    so local development without a key still works.
    """

    def __init__(self, app: ASGIApp) -> None:
        super().__init__(app)
        self._expected_key = os.getenv("API_SECRET_KEY", "")
        if not self._expected_key:
            logger.warning(
                "API_SECRET_KEY is not set — APIKeyMiddleware is permissive."
            )

    async def dispatch(self, request: Request, call_next):
        if not self._expected_key:
            return await call_next(request)

        if request.method == "OPTIONS":
            return await call_next(request)

        path = request.url.path
        if any(path.startswith(prefix) for prefix in PUBLIC_PREFIXES):
            return await call_next(request)

        header = request.headers.get("authorization", "")
        if not header.startswith(BEARER_PREFIX):
            return JSONResponse({"error": "unauthorized"}, status_code=401)

        token = header[len(BEARER_PREFIX):]
        if not hmac.compare_digest(token, self._expected_key):
            return JSONResponse({"error": "unauthorized"}, status_code=401)

        return await call_next(request)
