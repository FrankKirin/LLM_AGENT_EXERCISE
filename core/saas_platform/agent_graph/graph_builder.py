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
from sqlalchemy import select
from core.saas_platform.db.session import AsyncSessionLocal
from langgraph.graph import StateGraph, MessagesState
from core.saas_platform.models.plugin import AgentPlugin, TenantPluginRel, TenantTool
from core.saas_platform.plugins.plugin_loader import instantiate_plugin
from core.saas_platform.tool_market.dynamic_tool_builder import build_dynamic_tool 
from core.saas_platform.agent_graph.supervisor_node import build_supervisor_node
from langchain.messages import HumanMessage
from core.saas_platform.context.tool_context import ToolContext
from langgraph.graph import START, END
from langchain_core.tools import StructuredTool, tool
from langgraph.types import Command
from langgraph.prebuilt import ToolNode
from typing import Any
from langgraph.runtime import Runtime
from uuid import UUID
from core.langsmith_config import get_langsmith_tracer
from langchain_core.tools import InjectedToolCallId
from typing import Annotated
from langchain.messages import ToolMessage, AIMessage

# 显式引入langsmith的tracer
tracer = get_langsmith_tracer()

tenant_id = UUID("b7c84a42f0e941d29943d4f5e6f0f9da")
tool_context = ToolContext(tenant_id=tenant_id)

def build_worker_handoff_tool(worker_name: str):
    @tool(f"transfer_to_{worker_name}", description=f"将当前任务交给{worker_name}专项处理")
    async def handoff(tool_call_id: Annotated[str, InjectedToolCallId]):
        return Command(
            goto=worker_name,
            update={"messages":[
                ToolMessage(content=f"任务已转交给{worker_name}",
                name=f"transfer_to_{worker_name}",
                tool_call_id=tool_call_id,  # 闭环tool_call(不理解)
                ),
            ]},
        )
    return handoff

class AgentState(MessagesState):
    # {worker_name, worker_result}
    worker_result: dict[str, Any]

def to_text(data) -> str:
    if isinstance(data, str):
        return data
    return str(data)
    # if isinstance(data, list) and data and isinstance(data[0], dict):

# 子图结果转为父图结果
def build_worker_adapter(worker_name: str, worker_graph: Any):
    async def work_node(state: AgentState, runtime: Runtime[ToolContext]):
        # 调用子图
        result = await worker_graph.ainvoke(
            {"messages": state["messages"]},
            context=runtime.context,
        )
        print(f"{worker_name}子图返回的keys: {result.keys()}")
        final = result.get("result") or str(result)

        # ApiUsageState转换成AgentState
        return {
            "worker_result": {
                "worker_name": worker_name,
                "data": final,
            },
            "messages": [AIMessage(content=to_text(final), name=worker_name)]
        }
    return work_node

async def build_tenant_graph(tenant_id:UUID, db:AsyncSession):
    graph_builder = StateGraph(AgentState, context_schema=ToolContext)

    # 1.加载租户启用的插件, 装配成worker
    plugin_query = await db.execute(
        select(AgentPlugin, TenantPluginRel.plugin_config)
        .join(TenantPluginRel, AgentPlugin.id == TenantPluginRel.plugin_id)
        .where(TenantPluginRel.tenant_id==tenant_id, TenantPluginRel.enabled==True)
    )
    plugin_rows = plugin_query.all()
    avaliable_workers = []
    for plugin, cfg in plugin_rows:
        plugin_ins = instantiate_plugin(plugin.entry_cls, cfg)
        worker_name, worker_graph= plugin_ins.build_sub_graph()
        print(f"从数据库中找到调用的worker_name: {worker_name}\n\n woker_graph: {worker_graph}\n\n")
        worker_node = build_worker_adapter(
            worker_name,
            worker_graph,
        )
        # worker_node是包了一层的worker, 能把worker结果转换后给到supervisor
        graph_builder.add_node(worker_name, worker_node)
        avaliable_workers.append(worker_name)

    # 做成跳转tool
    handoff_tools = [
        build_worker_handoff_tool(worker_name) for worker_name in avaliable_workers
    ]

    # 2.加载租户自定义工具
    tool_query = await db.execute(
        select(TenantTool).where(TenantTool.tenant_id==tenant_id, TenantTool.enabled==True)
    )
    tenant_tools = []
    for tool_model in tool_query.scalars().all():
        dyn_tool = await build_dynamic_tool(
            tool_name=tool_model.tool_name,
            description=tool_model.description,
            run_code=tool_model.runnable_code,
            param_schema=tool_model.param_schema,
            context=tool_context,
        )
        tenant_tools.append(dyn_tool)
    # print(f"加载到的租户自定义工具: {tenant_tools}")

    supervisor_tools = [
        *tenant_tools,
        *handoff_tools,
    ]

    # 3.构建调度的图
    supervisor_node = build_supervisor_node(avaliable_workers, supervisor_tools)
    # 工具执行节点，负责执行superviosr发出来的tool call
    tool_node = ToolNode(supervisor_tools)

    graph_builder.add_node("supervisor", supervisor_node)
    graph_builder.add_node("supervisor_tools", tool_node)

    # 路由函数, 自动传入Graph State
    def route_supervisor(state):
        last = state["messages"][-1]
        if last.tool_calls:
            return "supervisor_tools"
        return END

    graph_builder.add_edge(
        START,
        "supervisor",
    )
    for worker in avaliable_workers:
        graph_builder.add_edge(worker, "supervisor")

    graph_builder.add_conditional_edges(
        "supervisor",
        route_supervisor,
        {
            "supervisor_tools": "supervisor_tools",
            END: END
        },
    )

    graph_builder.add_edge(
        "supervisor_tools",
        "supervisor",
    )

    return graph_builder.compile()

async def main_func():
    async with AsyncSessionLocal() as db:
        user_id = tenant_id
        graph = await build_tenant_graph(user_id, db)
        print(graph.get_graph().draw_mermaid())

        # test llm's tool
        query1 = f"帮我查询tenant_id为{user_id}的云盘剩余可用空间"
        query2 = f"帮我查询tenant_id为{user_id}的近7天api调用趋势"

        print(f"图中输入的问题{query2}\n\n")
        # 执行图的时候要把context传进去
        res = await graph.ainvoke(
            {
                "messages": [HumanMessage(content=query2)],
                "worker_result": {},
             },
             context=tool_context,
             config={
                 "callbacks": [tracer],
             },
        )

        print("*"*100)
        print("\n\n")
        print(f"res中worker_result结果{res['worker_result']}")

        print(f"图的执行结果: {res['messages'][-1].content}")

if __name__ == "__main__":
    import asyncio
    asyncio.run(main_func())
