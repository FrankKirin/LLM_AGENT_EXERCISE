import asyncio
from core.saas_platform.db.base import Base
from core.saas_platform.models.storage import StorageInfo
from core.saas_platform.models.tenant import Tenant, AgentConversation, TenantAgentConfig, TokenUsageLog
from core.saas_platform.models.plugin import AgentPlugin, TenantPluginRel, TenantTool
from core.saas_platform.db.session import async_engine
from core.structured_logger import log_info

async def init_tables():
    async with async_engine.begin() as conn:
        # create_all相当于不存在就创建，存在就跳过
        await conn.run_sync(Base.metadata.create_all)
        log_info("所有数据表创建完成")

if __name__ == "__main__":
    asyncio.run(init_tables())
