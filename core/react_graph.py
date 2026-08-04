import operator
from typing import TypedDict, Annotated, Sequence
from langchain.messages import AnyMessage, HumanMessage, ToolMessage, AIMessage
from langgraph.graph import START, END, StateGraph
from core.logger import logger
from core.config import settings
from core.rag_vector_store import get_retriever
from langchain_core.tools import StructuredTool
from core.lc_baseline import tools, llm
from langgraph.prebuilt import ToolNode
from langgraph.checkpoint.memory import MemorySaver
from core.config import settings

class AgentState(TypedDict):
    messages: Annotated[
        list[AnyMessage], operator.add
    ]

# 封装RAG检索为结构化工具
# 工具描述精准定义使用场景，引导
def rag_search(query: str) -> str:
    """从企业内部知识库中查询产品说明、操作手册、常见问题等文档内容。
       当用户询问产品使用、政策规则、常见问题时调用此工具。

       Args:
           query: 要查询的问题
    """
    retriever = get_retriever()
    docs = retriever.invoke(query)
    # 防止无意义的rag撑爆LLM上下文
    context = "\n\n".join([doc.page_content for doc in docs[:3]])

    if not context:
        return "知识库中未找到相关内容"
    return f"知识库参考内容：\n{context}"

# 转为结构化工具
rag_tool = StructuredTool.from_function(rag_search)

# 合并所有工具
all_tools = tools + [rag_tool]

async def agent_node(state:AgentState):
    # 避免长对话导致token超限
    # 生产环境可升级为 摘要+最近消息 的分层记忆方式
    messages = state["messages"]
    if len(messages) > 10:
        messages = messages[-10:]

    llm_with_tools = llm.bind_tools(all_tools)
    result = await llm_with_tools.ainvoke(state["messages"])
    return {"messages": [result]}

def handle_tool_error(error: Exception)->str:
    # 工具调用过程中发现抛出来的ERROR就会走进这个流程
    return f"工具调用失败: {repr(error)}, 请重新尝试"

tool_node = ToolNode(all_tools, handle_tool_errors=handle_tool_error)

# tool_node = ToolNode(all_tools, handle_tool_errors=True)
# tool_node = ToolNode(all_tools, handle_tool_errors="工具执行遇到异常，请检查输入或重试")


def should_continue(state:AgentState):
    last_msg = state["messages"][-1]
    if hasattr(last_msg, "tool_calls") and last_msg.tool_calls:
        return "tools"
    return END

memory_checkpointer = MemorySaver()

def build_production_agent():
    workflow = StateGraph(AgentState)

    workflow.add_node("agent", agent_node)
    workflow.add_node("tools", tool_node)

    workflow.add_edge(START, "agent")
    workflow.add_conditional_edges(
        "agent",
        should_continue,
        ["tools", END]
    )
    workflow.add_edge("tools", "agent")

    return workflow.compile(
        checkpointer=memory_checkpointer,
        interrupt_before=[],
        interrupt_after=[]
    )

if __name__ == "__main__":
    import os
    from pathlib import Path
    import asyncio
    workflow = build_production_agent()
    # 编译图时通过配置限制最大步数，防止LLM陷入无限工具调用
    config = {
        "configurable": {"thread_id": "user_002"},
        "recursion_limit": 10   # 最大执行10步，强制终止
    }
    # 配置了checkpointer，必须传递config
    res = asyncio.run(workflow.ainvoke(
            {"messages": [HumanMessage(content="石头机器人P10保修政策是怎么样的")]}, config=config
        )
    )

    logger.info(f"workflow调用结果:{res['messages'][-1].content}")