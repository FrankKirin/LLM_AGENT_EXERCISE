import asyncio
from core.saas_platform.db.base import Base
from core.saas_platform.db.models import Tenant, AgentConversation, TenantAgentConfig, TokenUsageLog
from core.saas_platform.db.session import async_engine
from core.structured_logger import log_info

async def init_tables():
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        log_info("所有数据表创建完成")

if __name__ == "__main__":
    asyncio.run(init_tables())