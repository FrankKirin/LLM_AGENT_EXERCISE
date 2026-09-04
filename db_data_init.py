import asyncio

from core.saas_platform.db.session import AsyncSessionLocal


from core.saas_platform.db.models import (
    Tenant,
    TenantAgentConfig,
    AgentConversation,
    TokenUsageLog,
)

async def init_data():
    async with AsyncSessionLocal() as db:

        tenant = Tenant(
            tenant_name="BYD",
            api_key="test-api-key-001",
            monthly_token_quota=1_000_000,
            is_active=True,
        )
        db.add(tenant)

        # flush后可以立即拿到tenant.id
        await db.flush()

        agent_config = TenantAgentConfig(
            tenant_id=tenant.id,
            system_prompt="你是一个专业的海运报价助手",
            model_name="deepseek_v4_flash",
            temperature=0.2,
        )
        db.add(agent_config)

        conversation = AgentConversation(
            tenant_id=tenant.id,
            thread_id="thread-001",
            title="上海到洛杉矶海运报价",
        )
        db.add(conversation)

        usage1 = TokenUsageLog(
            tenant_id=tenant.id,
            thread_id="thread-001",
            prompt_tokens=1000,
            completion_tokens=500,
        )
        usage2 = TokenUsageLog(
            tenant_id=tenant.id,
            thread_id="thread-001",
            prompt_tokens=800,
            completion_tokens=300,
        )
        db.add_all([usage1, usage2])

        await db.commit()
        print("测试数据写入成功")
        print("tenant_id", tenant.id)

if __name__ == "__main__":
    asyncio.run(init_data())

