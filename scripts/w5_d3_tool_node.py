from core.lc_baseline import tools
from core.logger import logger
from langgraph.prebuilt import ToolNode
from typing import TypedDict, Annotated, Literal
from langchain.messages import AIMessage, HumanMessage, ToolMessage, AnyMessage
import operator
from core.lc_baseline import llm, tools
from langgraph.graph import StateGraph, START, END
from core.logger import logger
from core.config import settings

class ReActState(TypedDict):
    messages: Annotated[list[AnyMessage], operator.add]


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

# async def execute_tool_node(state: ReActState):
#     tool_calls_res = state["messages"][-1].tool_calls
#     tool_res = []
#     for tool_call in tool_calls_res:
#         tool_map = {tool.name:tool for tool in tools}

#         if tool_call["name"] not in tool_map:
#             tool_res.append(
#                 ToolMessage(content=f"错误，不存在工具{tool_call['name']}", tool_call_id=tool_call.id)
#             )
#             continue
#         try:
#             result = tool_map[tool_call["name"]].invoke(tool_call["args"])
#             tool_res.append(
#                 ToolMessage(content=str(result), tool_call_id=tool_call["id"])
#             )
#         except Exception as e:
#             logger.error("工具执行异常", tool=tool_call["name"], error=str(e))
#             tool_res.append(
#                 ToolMessage(content=f"工具执行失败：{str(e)}", tool_call_id=tool_call["id"])
#             )

#     return {"messages": tool_res}
            

def should_continue(state: ReActState)->Literal["execute_tools", END]:
    msg = state["messages"][-1]
    if isinstance(msg, AIMessage) and msg.tool_calls:
        return "execute_tools"
    return END

def build_react_graph():
    workflow = StateGraph(ReActState)

    workflow.add_node("agent", agent_node)
    workflow.add_node("execute_tools", execute_tool_node)

    workflow.add_edge(START, "agent")
    workflow.add_conditional_edges(
        "agent",
        should_continue,
        ["execute_tools", END]
    )
    workflow.add_edge("execute_tools", "agent")

    return workflow.compile()

if __name__ == "__main__":
    import asyncio
    graph = build_react_graph()
    result = asyncio.run(graph.ainvoke({
        "messages":[HumanMessage(content="帮我查一下OD20260701的工单状态")]
    }))
    logger.info("ReAct执行完成", answer=result["messages"][-1].content)
    
