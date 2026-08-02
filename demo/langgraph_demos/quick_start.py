from langchain.tools import tool
from langchain_openai import ChatOpenAI
from core.logger import logger
from core.config import settings
from typing_extensions import TypedDict, Annotated
from langchain.messages import AnyMessage, SystemMessage, HumanMessage
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
logger.debug(f"tools_by_name内容：{tools_by_name}")

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

# 模型节点,节点功能为根据所有过去的Messages生成新的回复
# def llm_call(state: dict):
def llm_call(state: MessagesState):
    # 有个问题是每次都会塞SystemMessage，实际上只要塞一次就够
    state["llm_calls"] = state.get("llm_calls", 0) + 1
    if state["llm_calls"] == 1:
        system_prompt = SystemMessage(content="You are a helpful assistant tasked with performing arithmetic on a set of input")
        messages = [system_prompt] + state["messages"]
    else:
        messages = state["messages"]
    res = model_with_tools.invoke(messages)     # 这是一条AIMessage
    logger.debug(f"llm_call后调用的内容{res}")
    # Langgraph支持多种返回机制: LangGraph字典和Message对象, 字典是图里的全局对象
    return {"messages":[res], "llm_calls":state["llm_calls"]}

# 定义tool节点
# def tool_node(state: dict):
def tool_node(state: MessagesState):
    result = []
    logger.debug("state['messages'][-1]内容:", content=state['messages'][-1])
    for tool_call in state["messages"][-1].tool_calls:
        tool = tools_by_name[tool_call["name"]]
        observation = tool.invoke(tool_call["args"])
        logger.debug("observation内容:", observation=observation)
        result.append(ToolMessage(content=observation, tool_call_id=tool_call["id"]))
        logger.debug("result完整内容：", res=result)
    return {"messages": result}

# 路由函数，返回内容表示只能“tool_node或者END”
def should_continue(state: MessagesState) -> Literal["tool_node", END]:
    """Decide if we should continue the loop or stop based upon whether the LLM made a tool call"""

    last_message = state["messages"][-1]
    logger.debug("last['messages']里装了啥：", res=last_message)

    # 如果LLM执行tool call，执行一个操作
    logger.debug("message的tool_calls调用内容", res=last_message.tool_calls)
    if last_message.tool_calls:
        return "tool_node"

    return END


if __name__ == "__main__":
    logger.debug("tools_by_name属性",res=tools_by_name, type=type(tools_by_name))
    """
    # @tool可以通过invoke方法来调试
    print(multiply.invoke({"a":3, "b":4}))

    msg = model_with_tools.invoke(
        [
            HumanMessage(content="3 乘以 4等于多少？")
        ]
    )
    logger.debug("The content of msg tool_calls result", msg=msg.tool_calls)
    
    # 搭个最小图来跑通
    builder = StateGraph(MessagesState)
    builder.add_node("llm_call", llm_call)
    builder.add_edge(START, "llm_call")
    builder.add_edge("llm_call", END)
    graph = builder.compile()

    # 本质invoke函数传入的数据就是定义的MessageState
    result = graph.invoke({"messages":[HumanMessage(content="你好")]})
    print(result)
    """

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