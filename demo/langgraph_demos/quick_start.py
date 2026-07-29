from langchain.tools import tool
from langchain_openai import ChatOpenAI
from core.logger import logger
from core.config import settings
from typing_extensions import TypedDict, Annotated
from langchain.messages import AnyMessage, SystemMessage
import operator
from langchain.messages import ToolMessage
from typing import Literal
from langgraph.graph import StateGraph, START, END

llm = ChatOpenAI(
    base_url=settings.LLM_BASE_URL,
    api_key=settings.LLM_API_KEY,
    temperature=0.3,
    model=settings.LLM_MODEL,
    timeout=settings.LLM_TIMEOUT
)

# tool工具必须写好文档功能描述，"""描述内容"""
@tool
def multiply(a: int, b: int) -> int:
    """
    Multiply 'a' and 'b'

    Args:
        a: First int
        b: Second int
    """
    return a * b

@tool
def add(a: int, b: int) -> int:
    """
    Add 'a' and 'b'

    Args:
        a: First int
        b: Second int
    """
    return a + b

@tool
def divide(a: int, b: int) -> float:
    """
    Divide'a' and 'b'

    Args:
        a: First int
        b: Second int
    """
    return a / b

# 这里的tools是个tool函数对象列表，不是简单的函数名称列表
tools = [multiply, add, divide]
tools_by_name = {tool.name: tool for tool in tools}

# llm绑定工具
model_with_tools = llm.bind_tools(tools)

# state用于存储messages和LLM调用次数
# operator.add操作确保消息是追加而不是替换
class MessagesState(TypedDict):
    """messages: 保存当前Agent历史消息
       Anotated是python类型注解增强，额外告诉langgraph，多个节点更新messages，不要覆盖，用追加
       这是llm多轮对话的基础
    """
    messages: Annotated[list[AnyMessage], operator.add]
    llm_calls: int

# 模型节点
def llm_call(state: dict):
    return {
        "messages": [
            model_with_tools.invoke(
                [
                    SystemMessage(
                        content="You are a helpful assistant tasked with performing arithmetic on a set of input"
                    )
                ] + state["messages"]
            )
        ],
        # 记录llm_calls防止无限循环与成本控制
        "llm_calls": state.get("llm_calls", 0) + 1
    }

# 定义tool节点
def tool_node(state: dict):
    result = []
    logger.debug("state['messages'][-1]内容:", content=state['messages'][-1])
    for tool_call in state["messages"][-1].tool_calls:
        tool = tools_by_name[tool_call["name"]]
        observation = tool.invoke(tool_call["args"])
        logger.debug("observation内容:", observation=observation)
        result.append(ToolMessage(content=observation, tool_call_id=tool_call["id"]))
    return {"messages": result}

# 路由函数
# 返回类型没看懂
def should_continue(state: MessagesState) -> Literal["tool_node", END]:
    """Decide if we should continue the loop or stop based upon whether the LLM made a tool call"""

    messages = state["messages"]
    logger.debug("state['messages']里装了啥：", res=messages)
    last_message = messages[-1]
    logger.debug("last['messages']里装了啥：", res=last_message)

    # 如果LLM执行tool call，执行一个操作
    logger.debug("message的tool_calls调用内容", res=last_message.tool_calls)
    if last_message.tool_calls:
        return "tool_node"

    return END


if __name__ == "__main__":
    logger.debug("tools_by_name属性",res=tools_by_name, type=type(tools_by_name))

    # 构造workflow
    agent_builder = StateGraph(MessagesState)

    agent_builder.add_node("llm_call", llm_call)
    agent_builder.add_node("tool_node", tool_node)

    # START和END都算edge，不算node，是特殊的哨兵node
    # 从START流向 llm_call
    agent_builder.add_edge(START, "llm_call")

    agent_builder.add_conditional_edges(
        "llm_call",
        should_continue,
        ["tool_node", END]
    )

    # 如果分支走向tool_node，那么会再去到llm_call，构成循环
    agent_builder.add_edge("tool_node", "llm_call")

    agent = agent_builder.compile()

    from pathlib import Path
    Path("agent_graph.png").write_bytes(
        agent.get_graph(xray=True).draw_mermaid_png()
    )


    # Invoke
    from langchain.messages import HumanMessage
    messages = [HumanMessage(content="Divide 3 and 4.")]
    messages = agent.invoke({"messages": messages})
    for m in messages["messages"]:
        m.pretty_print()