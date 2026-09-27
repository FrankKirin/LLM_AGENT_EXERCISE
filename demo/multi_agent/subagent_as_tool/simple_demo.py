from typing import Annotated
from typing_extensions import TypedDict

from langchain.messages import (
    HumanMessage,
    AIMessage,
    ToolMessage,
)

from langchain_core.tools import tool

from langgraph.graph import (
    StateGraph,
    START,
    END,
)

from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode

# Researcher Agent
class ResearchState(TypedDict):
    messages: Annotated[list, add_messages]

@tool
def search_web(query: str)->str:
    """模拟搜索互联网资料"""
    print(f"\n[Search Tool]搜索: {query}")

    return (
        "LangGraph 是一个用于构建有状态 Agent 工作流的框架，"
        "核心概念包括 State、Node、Edge。"
    )

def researcher_llm(state: ResearchState):
    last_message = state["messages"][-1]

    # 第一次进入Researcher
    if isinstance(last_message, HumanMessage):
        print("\n[Researcher LLM] 我要先搜索资料")

        return {
            "messages": [
                AIMessage(content="", tool_calls=[
                    {
                        "name": "search_web",
                        "args": {
                            "query": last_message.content
                        },
                        "id": "research_call_1",
                    }
                ])
            ]
        }

    # Search Tool执行完
    if isinstance(last_message, ToolMessage):
        print("\n[Researcher LLM]已经拿到搜索结果")

        return {
            "messages": [AIMessage(content=("根据搜索结果，Langgraph是个用于构建"
                                            "有状态Agent工作流的框架"))]
        }

    raise ValueError("未知消息类型")

def researcher_route(state:ResearchState):
    last_message = state["messages"][-1]

    if last_message.tool_calls:
        return "research_tools"
    return END

# 构建Researcher Graph
researcher_builder = StateGraph(ResearchState)

researcher_builder.add_node("researcher_llm", researcher_llm)
researcher_builder.add_node("reserach_tools", ToolNode([search_web]))

researcher_builder.add_edge(START, "researcher_llm")

researcher_builder.add_conditional_edges("researcher_llm", researcher_route)

researcher_builder.add_edge("research_tools", "researcher_llm")

researcher_graph = researcher_builder.compile()

print(researcher_graph.get_graph().draw_mermaid())

# 把Researcher Agent包装成一个tool

@tool
def ask_researcher(task: str)->str:
    """让Researcher Agent独立完成一个研究任务"""

    print("[SubAgent Tool]启动Researcher")

    result = researcher_graph.invoke(
        {
            "messages": [HumanMessage(task)]
        }
    )
    return result["messages"][-1].content

# 三、Supervisor Agent

class SupervisorState(TypedDict):
    messages: Annotated[list, add_messages]