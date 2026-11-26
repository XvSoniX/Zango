from typing import AsyncGenerator
from contextlib import asynccontextmanager
from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine
)
from app.config import settings
from app.infrastructure.logging.logger import logger

def create_engine() -> AsyncEngine:
    db_url = settings.DATABASE_URL
    # For SQLite, pool_size / max_overflow / pool_recycle are not supported
    if "sqlite" in db_url:
        return create_async_engine(
            db_url,
            echo=settings.DB_ECHO,
            future=True
        )
    return create_async_engine(
        db_url,
        echo=settings.DB_ECHO,
        pool_size=settings.DB_POOL_SIZE,
        max_overflow=settings.DB_MAX_OVERFLOW,
        pool_timeout=settings.DB_POOL_TIMEOUT,
        pool_recycle=settings.DB_POOL_RECYCLE,
        pool_pre_ping=settings.DB_POOL_PRE_PING,
        future=True
    )

engine: AsyncEngine = create_engine()

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False
)

async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI Dependency for obtaining an async DB session with automatic commit on success."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            try:
                await session.commit()
            except Exception:
                await session.rollback()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()

@asynccontextmanager
async def transaction_scope() -> AsyncGenerator[AsyncSession, None]:
    """Context manager for programmatic atomic transactions in services."""
    async with AsyncSessionLocal() as session:
        async with session.begin():
            try:
                yield session
            except Exception as e:
                logger.error(f"Transaction rolled back due to error: {e}")
                await session.rollback()
                raise

async def check_db_health() -> bool:
    """Verifies that the database is reachable and accepting queries."""
    try:
        async with AsyncSessionLocal() as session:
            await session.execute(text("SELECT 1"))
            return True
    except Exception as e:
        logger.warning(f"Database health check failed: {e}")
        return False
