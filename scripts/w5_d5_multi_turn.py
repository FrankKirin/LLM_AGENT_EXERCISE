from core.config import settings
from langgraph.checkpoint.memory import MemorySaver
from core.logger import logger
from typing import Annotated, TypedDict, Literal
from langgraph.graph import StateGraph, END, START
from langchain.messages import AIMessage, ToolMessage, AnyMessage, HumanMessage
import operator
from langgraph.prebuilt import ToolNode
from core.lc_baseline import tools, llm
# 无需手动管理对话历史，调用时传入thread_id自动关联会话
# 支持断点续跑，断点恢复，适合人机介入
# 内存级存储，服务重启后丢失，仅用于开发测试
memory = MemorySaver()

class ReActState(TypedDict):
    # Annotated是给类型增加额外信息
    # 这里是在描述类型，所以只能是list[]
    messages: Annotated[
        list[AnyMessage], 
        operator.add
    ]

async def agent_node(state: ReActState):
    llm_with_tools = llm.bind_tools(tools)
    result = await llm_with_tools.ainvoke(state["messages"])    # ainvoke返回就是单个AIMessage对象
    return {"messages": [result]}

# ToolNode要求State必须包含messages字段，且最后一条带tool_calls的AIMessage
tool_node_func = ToolNode(tools)

def handle_tool_error(state: ReActState)->dict:
    error = state.get("error")
    tool_calls = state["messages"][-1].tool_calls
    return {
        "messages": [ToolMessage(content=f"工具执行出错：{repr(error)}, 请换一种方式提问", tool_call_id=tc["id"]) for tc in tool_calls]
    }

# 带错误兜底的工具节点
tool_node_with_retry = ToolNode(tools, handle_tool_errors=handle_tool_error)

def should_continue(state: ReActState)->Literal["execute_tools", END]:
    msg = state["messages"][-1]
    if isinstance(msg, AIMessage) and msg.tool_calls:
        return "execute_tools"
    return END

def build_persistent_react_graph():
    workflow = StateGraph(ReActState)

    workflow.add_node("agent", agent_node)
    workflow.add_node("execute_tools", tool_node_with_retry)

    workflow.add_edge(START, "agent")
    workflow.add_conditional_edges(
        "agent",
        should_continue,
        ["execute_tools", END]
    )
    workflow.add_edge("execute_tools", "agent")

    # 编译时传入checkpoint, 开启持久化
    return workflow.compile(checkpointer=memory)

"""
1.thread_id是会话的唯一标识：不同用户、不用场景用不同thread_id，天然隔离
2.状态全量持久化：不止对话历史，中间变量、工具调用记录全保存，完整回溯执行过程
3.上线时，将MemorySaver替换为RedisSaver，支持分布式部署、会话永久保存
"""

if __name__ == "__main__":
    import asyncio
    graph = build_persistent_react_graph()

    # 会话配置
    config = {"configurable": {"thread_id": "user_001"}}

    # 第一轮对话
    result1 = asyncio.run(graph.ainvoke(
        {"messages":[HumanMessage(content="你好，我想查工单")]},
        config=config
    ))
    logger.info("第一轮回复", content=result1["messages"][-1].content)


    result2 = asyncio.run(graph.ainvoke(
        {"messages":[HumanMessage(content="OD20260701这个")]},
        config=config
    ))
    logger.info("第二轮回复", content=result2["messages"][-1].content)