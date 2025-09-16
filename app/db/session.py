# app/db/session.py

from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase
from app.core.config import settings

# 1) Engine: one per app — async, resilient
engine = create_async_engine(
    settings.async_db_uri,
    pool_pre_ping=True,   # avoids stale connection errors
)

# 2) Session factory: creates short-lived sessions per request
AsyncSessionLocal = async_sessionmaker(
    engine,
    expire_on_commit=False,  # keep objects usable after commit
    class_=AsyncSession,
)

# 3) Declarative Base: all models inherit from this
class Base(DeclarativeBase):
    pass

# 4) FastAPI dependency: yields a session and closes it safely
async def get_session() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        yield session
