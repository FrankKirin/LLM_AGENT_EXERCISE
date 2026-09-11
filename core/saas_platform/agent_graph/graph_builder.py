"""
根据tenant_id查询该租户全部启用插件+自定义工具列表
循环实例化每一个插件，获取worker节点，全部注册到Supervisor-Worker主图
租户动态工具注入给Supervisor LLM绑定的tool_list
单元测试：模拟一个租户配置插件+自定义工具，构建完整graph，执行一次对话验证路由分发到自定义worker与动态工具
"""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from core.saas_platform.db.session import AsyncSessionLocal
from langgraph.graph import StateGraph, MessagesState
from core.saas_platform.models.plugin import AgentPlugin, TenantPluginRel, TenantTool
from core.saas_platform.plugins.plugin_loader import instantiate_plugin
from core.saas_platform.tool_market.dynamic_tool_builder import build_dynamic_tool 
from core.saas_platform.agent_graph.supervisor_graph import build_supervisor_node
from core.config import settings

async def build_tenant_graph(tenant_id:str, db:AsyncSession):
    graph_builder = StateGraph(MessagesState)

    # 1.加载租户启用的插件
    plugin_query = await db.execute(
        select(AgentPlugin, TenantPluginRel.plugin_config)
        .join(TenantPluginRel, AgentPlugin.id == TenantPluginRel.plugin_id)
        .where(TenantPluginRel.tenant_id==tenant_id, TenantPluginRel.enabled==True)
    )
    plugin_rows = plugin_query.all()
    worker_names = []
    for plugin, cfg in plugin_rows:
        plugin_ins = instantiate_plugin(plugin.entry_cls, cfg)
        node_name, node_func = plugin_ins.build_sub_graph()
        graph_builder.add_node(node_name, node_func)
        worker_names.append(node_name)

    # 2.加载租户自定义工具
    tool_query = await db.execute(
        select(TenantTool).where(TenantTool.tenant_id==tenant_id, TenantTool.enabled==True)
    )
    custom_tools = []
    for tool_model in tool_query.scalars().all():
        dyn_tool = build_dynamic_tool(
            tool_name=tool_model.tool_name,
            description=tool_model.description,
            param_schema=tool_model.param_schema,
            run_code=tool_model.runnable_code,
        )
        custom_tools.append(dyn_tool)

    # 3.Supervisor节点绑定动态工具列表
    supervisor_node = build_supervisor_node(worker_names, custom_tools)
    graph_builder.add_node("supervisor", supervisor_node)

    graph_builder.set_entry_point("supervisor")
    return graph_builder.compile()

async def main_func():
    async with AsyncSessionLocal() as db:
        graph = await build_tenant_graph("bc1e01f0-7e99-4db8-8980-9904db53ed95", db)
        

if __name__ == "__main__":
    import asyncio
    asyncio.run(main_func())
