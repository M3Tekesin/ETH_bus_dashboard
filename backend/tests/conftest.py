import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.auth import require_auth
from app.db import get_pool
from app.main import app


@pytest_asyncio.fixture
async def client():
    # Data-endpoint tests don't exercise auth; bypass it so they stay focused.
    # Auth itself is covered by test_auth.py via `raw_client` (no override).
    app.dependency_overrides[require_auth] = lambda: "test"
    transport = ASGITransport(app=app)
    async with app.router.lifespan_context(app):
        async with AsyncClient(transport=transport, base_url="http://test") as c:
            yield c
    app.dependency_overrides.pop(require_auth, None)


@pytest_asyncio.fixture
async def raw_client():
    # No auth override — used to test the real login + token enforcement.
    transport = ASGITransport(app=app)
    async with app.router.lifespan_context(app):
        async with AsyncClient(transport=transport, base_url="http://test") as c:
            yield c


@pytest_asyncio.fixture
async def clean_db(client):
    pool = get_pool()
    async with pool.acquire() as conn:
        await conn.execute("TRUNCATE telemetry")
    yield
