"""Optional HTTP Basic Auth when GM_COCKPIT_PASSWORD is set (tunnel / phone safe)."""

from __future__ import annotations

import base64
import binascii
import hashlib
import hmac

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.config import settings


def _digest(s: str) -> bytes:
    return hashlib.sha256(s.encode("utf-8")).digest()


def _const_eq(a: str, b: str) -> bool:
    return hmac.compare_digest(_digest(a), _digest(b))


def _www_authenticate() -> Response:
    return Response(
        status_code=401,
        headers={"WWW-Authenticate": 'Basic realm="GREEN MACHINE"'},
        content="Authentication required",
    )


class CockpitBasicAuthMiddleware(BaseHTTPMiddleware):
    """If ``GM_COCKPIT_PASSWORD`` is non-empty, require Basic auth (except OPTIONS + tiny allowlist)."""

    _EXEMPT_PATHS = frozenset({"/health", "/openapi.json", "/redoc"})
    _EXEMPT_PREFIXES = ("/docs",)

    async def dispatch(self, request: Request, call_next):
        pwd = settings.cockpit_password.strip()
        if not pwd:
            return await call_next(request)
        if request.method == "OPTIONS":
            return await call_next(request)
        path = request.url.path
        if path in self._EXEMPT_PATHS or any(path.startswith(p) for p in self._EXEMPT_PREFIXES):
            return await call_next(request)
        hdr = request.headers.get("authorization")
        if not hdr or not hdr.lower().startswith("basic "):
            return _www_authenticate()
        try:
            raw = base64.b64decode(hdr[6:].strip().encode("ascii"), validate=True).decode("utf-8")
        except (binascii.Error, UnicodeDecodeError, ValueError):
            return _www_authenticate()
        if ":" not in raw:
            return _www_authenticate()
        user, pw = raw.split(":", 1)
        if not _const_eq(user, settings.cockpit_user) or not _const_eq(pw, pwd):
            return _www_authenticate()
        return await call_next(request)
