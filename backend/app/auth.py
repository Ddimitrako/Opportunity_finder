from __future__ import annotations

import base64
import hashlib
import hmac
import json
import secrets
import time
from typing import Any

from fastapi import Response
from pydantic import BaseModel, Field

from app.config import Settings

PASSWORD_SCHEME = "pbkdf2_sha256"
PASSWORD_ITERATIONS = 600_000


class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=128)
    password: str = Field(min_length=1, max_length=256, repr=False)


class SessionResponse(BaseModel):
    authenticated: bool
    username: str | None = None


def hash_password(password: str, *, salt: bytes | None = None) -> str:
    if not password:
        raise ValueError("Password cannot be empty")
    password_salt = salt or secrets.token_bytes(18)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), password_salt, PASSWORD_ITERATIONS)
    return "$".join(
        (
            PASSWORD_SCHEME,
            str(PASSWORD_ITERATIONS),
            _encode(password_salt),
            _encode(digest),
        )
    )


def verify_password(password: str, encoded: str | None) -> bool:
    if not encoded:
        return False
    try:
        scheme, iterations_text, salt_text, digest_text = encoded.split("$", 3)
        iterations = int(iterations_text)
        salt = _decode(salt_text)
        expected = _decode(digest_text)
    except (TypeError, ValueError):
        return False
    if scheme != PASSWORD_SCHEME or iterations < PASSWORD_ITERATIONS or len(salt) < 16:
        return False
    actual = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)
    return hmac.compare_digest(actual, expected)


def credentials_are_valid(username: str, password: str, settings: Settings) -> bool:
    username_valid = secrets.compare_digest(username, settings.auth_username)
    password_valid = verify_password(password, settings.auth_password_hash)
    return username_valid and password_valid


def create_session_token(settings: Settings, *, now: int | None = None) -> str:
    issued_at = int(time.time() if now is None else now)
    payload = {
        "v": 1,
        "sub": settings.auth_username,
        "iat": issued_at,
        "exp": issued_at + settings.auth_session_hours * 3600,
    }
    encoded_payload = _encode(json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8"))
    signature = _sign(encoded_payload, settings)
    return f"{encoded_payload}.{signature}"


def session_username(token: str | None, settings: Settings, *, now: int | None = None) -> str | None:
    if not token or not settings.auth_secret_key:
        return None
    try:
        encoded_payload, supplied_signature = token.split(".", 1)
        if not hmac.compare_digest(_sign(encoded_payload, settings), supplied_signature):
            return None
        payload: dict[str, Any] = json.loads(_decode(encoded_payload))
        current_time = int(time.time() if now is None else now)
        if payload.get("v") != 1 or payload.get("sub") != settings.auth_username:
            return None
        if not isinstance(payload.get("iat"), int) or not isinstance(payload.get("exp"), int):
            return None
        if payload["iat"] > current_time + 60 or payload["exp"] <= current_time:
            return None
        return settings.auth_username
    except (UnicodeDecodeError, ValueError, TypeError, json.JSONDecodeError):
        return None


def set_session_cookie(response: Response, token: str, settings: Settings) -> None:
    response.set_cookie(
        key=settings.auth_cookie_name,
        value=token,
        max_age=settings.auth_session_hours * 3600,
        httponly=True,
        secure=settings.auth_cookie_secure,
        samesite="strict",
        path="/",
    )


def clear_session_cookie(response: Response, settings: Settings) -> None:
    response.delete_cookie(
        key=settings.auth_cookie_name,
        httponly=True,
        secure=settings.auth_cookie_secure,
        samesite="strict",
        path="/",
    )


def _sign(encoded_payload: str, settings: Settings) -> str:
    if not settings.auth_secret_key:
        raise ValueError("AUTH_SECRET_KEY is not configured")
    signature = hmac.new(settings.auth_secret_key.encode("utf-8"), encoded_payload.encode("ascii"), hashlib.sha256).digest()
    return _encode(signature)


def _encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode("ascii")


def _decode(value: str) -> bytes:
    padding = "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode(value + padding)
