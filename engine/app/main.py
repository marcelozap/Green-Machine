from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.cockpit_gate import CockpitBasicAuthMiddleware
from app.config import settings
from app.db import engine
from app.db_init import init_db_schema
from app.nexus.models import NexusBase
from app.routers import (
    backtest,
    desk,
    health,
    ingest_upload,
    live,
    nexus_auth,
    nexus_integrations,
    nexus_records,
)


def _cors_origins() -> list[str]:
    base = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ]
    extra = [o.strip() for o in settings.cors_origins.split(",") if o.strip()]
    return list(dict.fromkeys(base + extra))


@asynccontextmanager
async def lifespan(_: FastAPI):
    await init_db_schema(engine)
    async with engine.begin() as conn:
        await conn.run_sync(NexusBase.metadata.create_all)
    yield


app = FastAPI(title="GREEN MACHINE", version="1.0.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(CockpitBasicAuthMiddleware)

app.include_router(backtest.router)
app.include_router(desk.router)
app.include_router(health.router)
app.include_router(live.router)
app.include_router(ingest_upload.router)
app.include_router(nexus_auth.router)
app.include_router(nexus_records.router)
app.include_router(nexus_integrations.router)


@app.get("/api")
async def api_meta() -> dict[str, str]:
    return {
        "service": "green-machine",
        "docs": "/docs",
        "nexus": "/nexus/records",
        "voice": "/auth/voice-pass",
    }


_COCKPIT = Path(__file__).resolve().parents[1] / "static" / "cockpit"
if _COCKPIT.is_dir() and any(_COCKPIT.iterdir()):
    app.mount("/", StaticFiles(directory=str(_COCKPIT), html=True), name="cockpit")
