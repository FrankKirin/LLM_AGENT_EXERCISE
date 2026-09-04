from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from core.saas_platform.db.base import db_settings

async_engine = create_async_engine(
    db_settings.DATABASE_URL,
    echo=db_settings.DB_ECHO,
    pool_pre_ping=True
)

# 这是一个数据库异步session工厂
AsyncSessionLocal = async_sessionmaker(
    bind=async_engine,
    expire_on_commit=False
)

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    # FastAPI异步数据库会话依赖注入代码Depends(get_db)
    async with AsyncSessionLocal() as session:  # 本质是async_sessionmaker()
        yield session