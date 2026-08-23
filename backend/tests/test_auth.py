from unittest.mock import patch

from fastapi.testclient import TestClient

from app.auth import create_session_token, hash_password, session_username, verify_password
from app.config import Settings, get_settings
from app.main import app


def auth_settings() -> Settings:
    return Settings(
        auth_required=True,
        auth_username="operator",
        auth_password_hash=hash_password("correct horse battery staple"),
        auth_secret_key="test-secret-key-that-is-longer-than-thirty-two-characters",
        auth_cookie_secure=False,
        auth_session_hours=1,
    )


def test_password_hash_and_session_tokens_reject_invalid_values() -> None:
    settings = auth_settings()
    assert verify_password("correct horse battery staple", settings.auth_password_hash)
    assert not verify_password("wrong password", settings.auth_password_hash)

    token = create_session_token(settings, now=1_000)
    assert session_username(token, settings, now=1_001) == "operator"
    assert session_username(f"{token}tampered", settings, now=1_001) is None
    assert session_username(token, settings, now=4_601) is None


def test_protected_routes_require_login_and_logout_clears_session() -> None:
    settings = auth_settings()
    app.dependency_overrides[get_settings] = lambda: settings
    try:
        with patch("app.main.get_settings", return_value=settings):
            with TestClient(app) as client:
                assert client.get("/api/health").status_code == 200
                assert client.get("/api/config").status_code == 401
                assert client.get("/api/auth/session").json() == {"authenticated": False, "username": None}

                rejected = client.post(
                    "/api/auth/login",
                    json={"username": "operator", "password": "wrong password"},
                )
                assert rejected.status_code == 401

                accepted = client.post(
                    "/api/auth/login",
                    json={"username": "operator", "password": "correct horse battery staple"},
                )
                assert accepted.status_code == 200
                assert accepted.json() == {"authenticated": True, "username": "operator"}
                cookie = accepted.headers["set-cookie"].lower()
                assert "httponly" in cookie
                assert "samesite=strict" in cookie

                assert client.get("/api/config").status_code == 200
                assert client.get("/api/auth/session").json() == {"authenticated": True, "username": "operator"}

                logged_out = client.post("/api/auth/logout")
                assert logged_out.status_code == 200
                assert logged_out.json() == {"authenticated": False, "username": None}
                assert client.get("/api/config").status_code == 401
    finally:
        app.dependency_overrides.clear()
