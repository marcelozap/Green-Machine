from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.db import engine
from app.db_init import init_db_schema
from app.routers import backtest, health


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
    yield


app = FastAPI(title="GREEN MACHINE", version="1.0.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(backtest.router)
app.include_router(health.router)


@app.get("/")
async def root() -> dict[str, str]:
    return {"service": "green-machine", "docs": "/docs"}
