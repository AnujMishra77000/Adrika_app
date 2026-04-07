from collections.abc import AsyncGenerator

from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import get_settings

settings = get_settings()

database_url = make_url(settings.database_url)
engine_kwargs = {
    "echo": False,
    "pool_pre_ping": True,
    "future": True,
}

# SQLite local development does not benefit from pre-ping and needs thread-safe connect args.
if database_url.get_backend_name() == "sqlite":
    engine_kwargs["pool_pre_ping"] = False
    engine_kwargs["connect_args"] = {"check_same_thread": False}

engine = create_async_engine(
    settings.database_url,
    **engine_kwargs,
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    autoflush=False,
    autocommit=False,
    expire_on_commit=False,
)


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        yield session
