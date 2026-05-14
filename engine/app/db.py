from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import settings


def _engine_kwargs(url: str) -> dict:
    if url.strip().lower().startswith("sqlite"):
        return {"connect_args": {"check_same_thread": False}}
    return {}


engine = create_async_engine(settings.database_url, echo=False, **_engine_kwargs(settings.database_url))
SessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    async with SessionLocal() as session:
        yield session
