import asyncio
import random
from sqlalchemy import select, text, delete
from core.saas_platform.db.session import AsyncSessionLocal
from core.saas_platform.models.storage import StorageInfo
from core.saas_platform.models.tenant import (Tenant, TenantAgentConfig, AgentConversation, TokenUsageLog)
from core.saas_platform.models.plugin import (AgentPlugin, TenantPluginRel, TenantTool)
from uuid import UUID
import textwrap

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

async def init_token_usage(tenant_id:UUID):
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
        await db.execute(delete(AgentPlugin))
        await db.commit()

        weather = AgentPlugin(
            plugin_key="weather",
            plugin_name="get_weather",
            entry_cls="core.saas_platform.plugins.fetch_weather:FetchWeather",
            config_schema={"location":"Shanghai"},
            is_public=True,
        )
        db.add(weather)
        await db.commit()
        print(f"plugin插件数据写入成功:{weather}, weather_id: {weather.id}")

        query_storage = AgentPlugin(
            plugin_key="api_usage",
            plugin_name="fetch_storage_info",
            entry_cls="core.saas_platform.plugins.api_usage:ApiUsage",
            config_schema={"tenant_id":""},
            is_public=False
        )
        db.add(query_storage)
        await db.commit()

        print(f"plugin插件数据写入成功:{query_storage}, storate_id: {query_storage.id}")


async def init_tenantpluginrel(tenant_id:UUID):
    async with AsyncSessionLocal() as db:
        await db.execute(delete(TenantPluginRel))
        await db.commit()
        # tenant_id = await db.scalars(select(Tenant.id))
        # tenant_id = tenant_id
        # agentplugin_id = await db.scalars(select(AgentPlugin.id))

        # selected_tenant_id = random.choice(list(tenant_id))
        selected_tenant_id = tenant_id
        # selected_agentplugin_id = random.choice(list(agentplugin_id))
        selected_agentplugin_id = 2

        rel1 = TenantPluginRel(
            tenant_id=selected_tenant_id,
            plugin_id=1,
            plugin_config={"default_location":"Beijing"},
            enabled=True,
        )
        rel2 = TenantPluginRel(
            tenant_id=selected_tenant_id,
            plugin_id=selected_agentplugin_id,
            plugin_config={},
            enabled=True,
        )
        db.add_all([rel1, rel2])
        await db.commit()

        print("agent_plugin_rel写入成功")

async def init_tenanttool(tenant_id:UUID):
    async with AsyncSessionLocal() as db:
        # tenant_id = await db.scalars(select(Tenant.id))
        # selected_tenant_id = random.choice(list(tenant_id))
        selected_tenant_id = tenant_id
        await db.execute(delete(TenantTool))
        await db.commit()

        tenant_tool1 = TenantTool(
            tenant_id=selected_tenant_id,
            tool_name="calculate_add",
            description="计算两个整数的和",
            param_schema={"a":"int", "b":"int"},
            runnable_code=textwrap.dedent("""def tool_func(a:int, b:int):
                            return a+b""").strip(),
            enabled=True, 
        )
        run_code ="""
                from uuid import UUID
                async def tool_func(tenant_id:UUID)->int:
                    async with AsyncSessionLocal() as db:
                        rows = await db.execute(select(StorageInfo)
                                                .where(StorageInfo.tenant_id == tenant_id))
                        res = rows.scalar_one_or_none()
                        return res.remaining_space if res else 0
                """
        tenant_tool2 = TenantTool(
            tenant_id=selected_tenant_id,
            tool_name="fetch_storage_info",
            description="获取用户剩余可用云盘空间",
            param_schema={"tenant_id":"UUID"},
            runnable_code=textwrap.dedent(run_code).strip(),
            enabled=True, 
        )
        tenant_tools = [tenant_tool1, tenant_tool2]

        db.add_all(tenant_tools)
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
        await db.execute(delete(StorageInfo))
        await db.commit()
        print(f"storage_info表内容已清空")

if __name__ == "__main__":

    user_id = UUID("b7c84a42f0e941d29943d4f5e6f0f9da")
    # asyncio.run(drop_tenant_tool())

    ### operate storage_info
    # asyncio.run(init_storage_info())
    # asyncio.run(drop_storage_info())

    ### operate token_usage_log
    # asyncio.run(init_token_usage(user_id))

    ### init_agent_plugin
    # asyncio.run(init_agentplugin())

    ## init_tenant_plugin_rel
    # asyncio.run(init_tenantpluginrel(user_id))

    ### init_agent_tools
    asyncio.run(init_tenanttool(user_id))