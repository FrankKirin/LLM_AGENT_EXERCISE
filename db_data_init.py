import asyncio
import random
from sqlalchemy import select, text, delete
from core.saas_platform.db.session import AsyncSessionLocal
from core.saas_platform.models.storage import StorageInfo
from core.saas_platform.models.tenant import (Tenant, TenantAgentConfig, AgentConversation, TokenUsageLog)
from core.saas_platform.models.plugin import (AgentPlugin, TenantPluginRel, TenantTool)
from uuid import UUID

# Init Table data
async def tenant_init_data():
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
            model_name="deepseek-ai/DeepSeek-V3.2",
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
        print("tenant数据写入成功")
        print("tenant_id", tenant.id)

async def init_token_usage(tenant_id:UUID=UUID("bc1e01f0-7e99-4db8-8980-9904db53ed95")):
    async with AsyncSessionLocal() as db:
        token_use = TokenUsageLog(
            tenant_id=tenant_id,
            thread_id="thread-001",
            prompt_tokens=random.randint(200, 2000),
            completion_tokens=random.randint(1000, 100000)
        )
        db.add(token_use)
        await db.commit()
        print(f"Token使用记录添加成功：{token_use}")


async def init_agentplugin():
    async with AsyncSessionLocal() as db:
        agentplugin = AgentPlugin(
            plugin_key="weather",
            plugin_name="get_weather",
            entry_cls="core.saas_platform.plugins",
            config_schema={"location":"Shanghai"},
            is_public=True,
        )
        db.add(agentplugin)
        await db.commit()
        print("agent plugin数据写入成功")

async def init_tenantpluginrel():
    async with AsyncSessionLocal() as db:
        tenant_id = await db.scalars(select(Tenant.id))
        agentplugin_id = await db.scalars(select(AgentPlugin.id))

        selected_tenant_id = random.choice(list(tenant_id))
        selected_agentplugin_id = random.choice(list(agentplugin_id))

        rel = TenantPluginRel(
            tenant_id=str(selected_tenant_id),
            plugin_id=selected_agentplugin_id,
            plugin_config={"default_location":"Beijing"},
            enabled=True,
        )
        db.add(rel)
        await db.commit()

        print("agent_plugin_rel写入成功")

async def init_tenanttool():
    async with AsyncSessionLocal() as db:
        tenant_id = await db.scalars(select(Tenant.id))
        selected_tenant_id = random.choice(list(tenant_id))

        tenant_tool = TenantTool(
            tenant_id=str(selected_tenant_id),
            tool_name="calculate_add",
            description="计算两个整数的和",
            param_schema={"a":"int", "b":"int"},
            runnable_code="""def tool_func(a:int, b:int):
                            return a+b""",
            enabled=True, 
        )
        db.add(tenant_tool)
        await db.commit()

async def init_storage_info():
    async with AsyncSessionLocal() as db:

        
        tenant_ids = await db.scalars(select(Tenant.id))    # 返回一个迭代器
        for tenant_id in tenant_ids:
            storage = StorageInfo(
                tenant_id=tenant_id,
                used_space=random.randint(200, 50000)
            )
            db.add(storage)
            await db.commit()
            await db.flush()
            print(f"新建storage_info对象成功: {storage}")
        

# drop table
async def drop_tenant_tool():
    async with AsyncSessionLocal() as db:
        await db.execute(text("DROP TABLE tenant_tool"))
        await db.commit()
        print("drop table tenant_tool success!")

async def drop_storage_info():
    async with AsyncSessionLocal() as db:
        stmt = await db.execute(delete(StorageInfo))
        await db.commit()
        print(f"storage_info表内容已清空")

if __name__ == "__main__":

    # asyncio.run(drop_tenant_tool())

    # operate storage_info
    # asyncio.run(init_storage_info())
    # asyncio.run(drop_storage_info())


    # operate token_usage_log
    asyncio.run(init_token_usage())

