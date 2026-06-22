from __future__ import annotations

from datetime import datetime, timedelta, timezone

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from .config import settings

_hasher = PasswordHasher()
_bearer = HTTPBearer(auto_error=False)
_ALGORITHM = "HS256"


def verify_credentials(username: str, password: str) -> bool:
    """True only if the username matches and the password verifies against the
    configured Argon2 hash."""
    if not settings.auth_password_hash or username != settings.auth_username:
        return False
    try:
        return _hasher.verify(settings.auth_password_hash, password)
    except VerifyMismatchError:
        return False


def create_token(username: str) -> str:
    """Issue a JWT signed with HMAC-SHA256, expiring after the configured TTL."""
    now = datetime.now(timezone.utc)
    payload = {
        "sub": username,
        "iat": now,
        "exp": now + timedelta(hours=settings.jwt_ttl_hours),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=_ALGORITHM)


def require_auth(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> str:
    """FastAPI dependency: reject requests without a valid bearer token,
    otherwise return the authenticated username."""
    if credentials is None:
        raise HTTPException(status_code=401, detail="Not authenticated")
    try:
        payload = jwt.decode(
            credentials.credentials, settings.jwt_secret, algorithms=[_ALGORITHM]
        )
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    return payload.get("sub", "")
