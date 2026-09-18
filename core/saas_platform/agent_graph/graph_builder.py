"""
根据tenant_id查询该租户全部启用插件+自定义工具列表
循环实例化每一个插件，获取worker节点，全部注册到Supervisor-Worker主图
租户动态工具注入给Supervisor LLM绑定的tool_list
单元测试：模拟一个租户配置插件+自定义工具，构建完整graph，执行一次对话验证路由分发到自定义worker与动态工具
"""
import dotenv
dotenv.load_dotenv(override=True)
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, Uuid
from core.saas_platform.db.session import AsyncSessionLocal
from langgraph.graph import StateGraph, MessagesState
from core.saas_platform.models.plugin import AgentPlugin, TenantPluginRel, TenantTool
from core.saas_platform.plugins.plugin_loader import instantiate_plugin
from core.saas_platform.tool_market.dynamic_tool_builder import build_dynamic_tool 
from core.saas_platform.agent_graph.supervisor_graph import build_supervisor_node
from langchain.messages import HumanMessage

async def build_tenant_graph(tenant_id:UUID, db:AsyncSession):
    graph_builder = StateGraph(MessagesState)

    print(f"tenant_id内容: {tenant_id}, type: {type(tenant_id)}")

    # # 1.加载租户启用的插件, 装配成worker
    plugin_query = await db.execute(
        select(AgentPlugin, TenantPluginRel.plugin_config)
        .join(TenantPluginRel, AgentPlugin.id == TenantPluginRel.plugin_id)
        .where(TenantPluginRel.tenant_id==tenant_id, TenantPluginRel.enabled==True)
    )
    plugin_rows = plugin_query.all()
    print(f"找到符合要求的plugin有{plugin_rows}")
    worker_names = []
    for plugin, cfg in plugin_rows:
        plugin_ins = instantiate_plugin(plugin.entry_cls, cfg)
        node_name, node_func = plugin_ins.build_sub_graph()
        graph_builder.add_node(node_name, node_func)
        worker_names.append(node_name)

    # print(f"从plugin读取的worker组装完毕：共有这些worker{worker_names}")

    # 2.加载租户自定义工具
    tool_query = await db.execute(
        select(TenantTool).where(TenantTool.tenant_id==tenant_id, TenantTool.enabled==True)
    )
    # print(f"tool_query内容:{tool_query.scalars().all()}")
    custom_tools = []
    for tool_model in tool_query.scalars().all():
        dyn_tool = build_dynamic_tool(
            tool_name=tool_model.tool_name,
            description=tool_model.description,
            param_schema=tool_model.param_schema,
            run_code=tool_model.runnable_code,
        )
        custom_tools.append(dyn_tool)
    print(f"加载到的租户自定义工具: {custom_tools}")
    # 3.Supervisor节点绑定动态工具列表
    supervisor_node = build_supervisor_node(worker_names, custom_tools)
    graph_builder.add_node("supervisor", supervisor_node)

    graph_builder.set_entry_point("supervisor")
    return graph_builder.compile()

async def main_func():
    async with AsyncSessionLocal() as db:
        user_id = UUID("b7c84a42f0e941d29943d4f5e6f0f9da")
        graph = await build_tenant_graph(user_id, db)
        await graph.ainvoke(
            {"messages": [HumanMessage(content="帮我查询tenant_id为{user_id}的api调用趋势")]}
        )
        print(graph.get_graph().draw_mermaid())

if __name__ == "__main__":
    import asyncio
    asyncio.run(main_func())
