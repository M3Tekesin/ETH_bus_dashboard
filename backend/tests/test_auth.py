import pytest
from argon2 import PasswordHasher

from app.config import settings

pytestmark = pytest.mark.asyncio

PASSWORD = "correct horse battery staple"


@pytest.fixture(autouse=True)
def _configure_auth():
    # Configure known credentials for the duration of each test.
    prev = (settings.auth_username, settings.auth_password_hash, settings.jwt_secret)
    settings.auth_username = "admin"
    settings.auth_password_hash = PasswordHasher().hash(PASSWORD)
    settings.jwt_secret = "test-secret-0123456789abcdef0123456789abcdef"
    yield
    (settings.auth_username, settings.auth_password_hash, settings.jwt_secret) = prev


async def test_login_success_returns_token(raw_client):
    resp = await raw_client.post(
        "/api/login", json={"username": "admin", "password": PASSWORD}
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["token_type"] == "bearer"
    assert body["access_token"]


async def test_login_wrong_password_401(raw_client):
    resp = await raw_client.post(
        "/api/login", json={"username": "admin", "password": "nope"}
    )
    assert resp.status_code == 401


async def test_protected_endpoint_without_token_401(raw_client):
    assert (await raw_client.get("/api/buses")).status_code == 401


async def test_protected_endpoint_with_token_ok(raw_client):
    token = (await raw_client.post(
        "/api/login", json={"username": "admin", "password": PASSWORD}
    )).json()["access_token"]
    resp = await raw_client.get(
        "/api/buses", headers={"Authorization": f"Bearer {token}"}
    )
    assert resp.status_code == 200


async def test_health_is_public(raw_client):
    assert (await raw_client.get("/api/health")).status_code == 200
