"""
VS-9 Smart Alerts Ecosystem - Authentication, authorization, and rate limiting.

The API can run in development without auth by leaving OPTIX_AUTH_REQUIRED=false.
Production deployments should set OPTIX_AUTH_REQUIRED=true and provide
OPTIX_JWT_SECRET or OPTIX_JWT_PUBLIC_KEY.
"""

from __future__ import annotations

import os
import time
from dataclasses import dataclass
from typing import Dict, Optional

from fastapi import Depends, Header, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

try:  # pragma: no cover - dependency availability depends on deployment image
    import jwt
except ImportError:  # pragma: no cover
    jwt = None


security = HTTPBearer(auto_error=False)


@dataclass
class AuthenticatedUser:
    user_id: str
    tenant_id: Optional[str] = None
    role: str = "user"
    scopes: tuple[str, ...] = ()


def auth_required() -> bool:
    return os.getenv("OPTIX_AUTH_REQUIRED", "false").lower() == "true"


def get_current_user(credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)) -> AuthenticatedUser:
    """Resolve the current user from a JWT bearer token.

    Development mode returns a deterministic local user to preserve current tests
    and demos. Production mode requires PyJWT and a valid token.
    """
    if not auth_required():
        return AuthenticatedUser(user_id=os.getenv("OPTIX_DEV_USER_ID", "demo-user"), role="admin", scopes=("*",))

    if credentials is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing bearer token")
    if jwt is None:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="PyJWT is required for JWT auth")

    secret = os.getenv("OPTIX_JWT_SECRET") or os.getenv("OPTIX_JWT_PUBLIC_KEY")
    algorithm = os.getenv("OPTIX_JWT_ALGORITHM", "HS256")
    if not secret:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="JWT secret/public key not configured")

    try:
        payload = jwt.decode(credentials.credentials, secret, algorithms=[algorithm], audience=os.getenv("OPTIX_JWT_AUDIENCE"))
    except Exception as exc:  # pragma: no cover - token-specific
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=f"Invalid token: {exc}") from exc

    return AuthenticatedUser(
        user_id=str(payload.get("sub") or payload.get("user_id")),
        tenant_id=payload.get("tenant_id"),
        role=payload.get("role", "user"),
        scopes=tuple(payload.get("scopes", [])),
    )


def require_user_access(target_user_id: str, current_user: AuthenticatedUser) -> None:
    """Ensure the current user can access a user's resources."""
    if current_user.role in {"admin", "service"} or "*" in current_user.scopes:
        return
    if current_user.user_id != target_user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized for this user")


class InMemoryRateLimiter:
    """Simple sliding-window rate limiter for API protection."""

    def __init__(self, max_requests: int = 120, window_seconds: int = 60):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._requests: Dict[str, list[float]] = {}

    def check(self, key: str) -> None:
        now = time.time()
        window_start = now - self.window_seconds
        entries = [ts for ts in self._requests.get(key, []) if ts >= window_start]
        if len(entries) >= self.max_requests:
            raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="Rate limit exceeded")
        entries.append(now)
        self._requests[key] = entries


_rate_limiter = InMemoryRateLimiter(
    max_requests=int(os.getenv("OPTIX_RATE_LIMIT_REQUESTS", "120")),
    window_seconds=int(os.getenv("OPTIX_RATE_LIMIT_WINDOW_SECONDS", "60")),
)


async def enforce_rate_limit(request: Request, current_user: AuthenticatedUser = Depends(get_current_user)) -> None:
    key = current_user.user_id or request.client.host if request.client else "anonymous"
    _rate_limiter.check(key)


def verify_api_key(x_api_key: Optional[str] = Header(default=None)) -> None:
    """Validate optional external integration API key."""
    configured = os.getenv("OPTIX_EXTERNAL_API_KEY")
    if not configured:
        return
    if x_api_key != configured:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API key")
