import logging
import sys
import os
from uuid import uuid4
from contextlib import asynccontextmanager
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from config import settings
from redis.asyncio import Redis

# Ensure parent directory is in path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Configure logger
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("reelise_worker")

# Initialize database engine
DATABASE_URL = settings.DATABASE_URL
# Convert potential postgres:// to postgresql+asyncpg:// for async pg compatibility
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql+asyncpg://", 1)
elif DATABASE_URL.startswith("postgresql://"):
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://", 1)

engine = create_async_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    pool_size=5,
    max_overflow=10,
    connect_args={
        "statement_cache_size": 0,
        "prepared_statement_cache_size": 0,
        "prepared_statement_name_func": lambda: f"__asyncpg_{uuid4().hex}__"
    }
)

SessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False
)

# Initialize Redis client
redis_client = Redis.from_url(settings.REDIS_URL, decode_responses=True)

@asynccontextmanager
async def get_worker_db():
    """
    Context manager to yield a new scoped async session for worker database operations.
    """
    session = SessionLocal()
    try:
        yield session
    except Exception as e:
        logger.error(f"Worker database transaction error: {str(e)}")
        await session.rollback()
        raise
    finally:
        await session.close()
