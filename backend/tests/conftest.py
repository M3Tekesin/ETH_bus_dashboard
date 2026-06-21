import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.db import get_pool


@pytest_asyncio.fixture
async def client():
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
