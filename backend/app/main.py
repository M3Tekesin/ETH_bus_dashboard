from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import settings
from .db import create_pool, set_pool
from .routers import ingest, query

SCHEMA = Path(__file__).parent / "schema.sql"


@asynccontextmanager
async def lifespan(app: FastAPI):
    pool = await create_pool()
    set_pool(pool)
    async with pool.acquire() as conn:
        await conn.execute(SCHEMA.read_text())
    yield
    await pool.close()
    set_pool(None)


app = FastAPI(title="Telemetry Analytics API", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(ingest.router)
app.include_router(query.router)


@app.get("/api/health")
async def health():
    return {"status": "ok"}
