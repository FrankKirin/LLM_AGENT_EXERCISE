"""
根据tenant_id查询该租户全部启用插件+自定义工具列表
循环实例化每一个插件，获取worker节点，全部注册到Supervisor-Worker主图
租户动态工具注入给Supervisor LLM绑定的tool_list
单元测试：模拟一个租户配置插件+自定义工具，构建完整graph，执行一次对话验证路由分发到自定义worker与动态工具
"""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from langgraph.graph import StateGraph, MessagesState
from core.saas_platform.models.plugin import AgentPlugin, TenantPluginRel, CustomTool
from core.saas_platform.plugins.plugin_loader import instantiate_plugin


async def build_tenant_graph(tenant_id:str, db:AsyncSession):
    graph_builder = StateGraph(MessagesState)

    # 1.加载租户启用插件
    plugin_query = await db.execute(
        select(AgentPlugin, TenantPluginRel.plugin_config)
        .join(TenantPluginRel, AgentPlugin.id == TenantPluginRel.plugin_id)
        .where(TenantPluginRel.tenant_id==tenant_id, TenantPluginRel.enabled==True)
    )
    plugin_rows = plugin_query.all()
    worker_names = []
    for plugin, cfg in plugin_rows:
        plugin_ins = instantiate_plugin(plugin, cfg)
        node_name, node_func = plugin_ins.build_sub_graph()
        graph_builder.add_node(node_name, node_func)
        worker_names.append(node_name)

    return graph_builder, worker_names

    # # 2.加载租户自定义工具(绑定给supervisor)
    # tool_query = await db.execute(
    #     select(CustomTool.description, CustomTool.description, 
    #            CustomTool.param_schema, CustomTool.runnable_code)
    #            .where(CustomTool.tenant_id == tenant_id)
    # )
    # tool_rows = tool_query.all()
