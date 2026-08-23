"""
JARVIS AI - Database Module

Database connection and session management using SQLAlchemy async.
Supports both SQLite (development) and PostgreSQL (production).
"""

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from typing import AsyncGenerator
import logging

from config import settings, get_settings

logger = logging.getLogger(__name__)


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy models"""
    pass


# Create async engine
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.ECHO_SQL,
    future=True,
)

# Create async session factory
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency for FastAPI to get database session.
    
    Usage:
        @app.get("/items")
        async def get_items(db: AsyncSession = Depends(get_db)):
            ...
    """
    db = AsyncSessionLocal()
    try:
        yield db
    finally:
        await db.close()


async def init_db():
    """
    Initialize database tables.
    Call this on application startup.
    """
    try:
        # Ensure directories exist
        import os
        if settings.DATABASE_TYPE == "sqlite":
            db_dir = os.path.dirname(settings.SQLITE_PATH)
            if db_dir:
                os.makedirs(db_dir, exist_ok=True)
        
        # Create all tables
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        raise


async def close_db():
    """
    Close database connections.
    Call this on application shutdown.
    """
    await engine.dispose()
    logger.info("Database connections closed")
