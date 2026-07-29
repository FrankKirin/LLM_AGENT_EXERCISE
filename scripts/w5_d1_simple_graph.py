from typing import TypedDict, Annotated, Sequence
from langchain_core.messages import BaseMessage, HumanMessage
import operator
from core.lc_baseline import llm
from langgraph.graph import StateGraph, START, END
from core.logger import logger

class AgentState(TypedDict):
    # operator.add使得每次message不是覆盖而是追加
    messages: Annotated[Sequence[BaseMessage], operator.add]

# 定义节点函数, 所有节点函数入参都是完整State，返回值是要更新的状态字段
# 意图分类节点，判断用户问题是闲聊还是需要工具查询
async def intent_classify_node(state: AgentState):
    prompt = f"""
    判断用户问题属于以下哪一类，只输出分类编号：
    1.工单/客户信息查询
    2.普通闲聊

    用户问题：{state["messages"][-1].content}
    """
    res = await llm.ainvoke(prompt)
    return {"messages": [res]}


async def chat_node(state: AgentState):
    res = await llm.ainvoke("你是友好的客服助手，简洁回复用户问题： " + state['messages'][-1].content)
    return {"messages": [res]}


async def tool_node(state: AgentState):
    return {"messages": [{"role": "assistant", "content":"即将调用工具查询"}]}


# 条件路由器函数
# 根据意图分类结果，决定下一个执行的节点
# 返回值必须是节点名称字符串，或END表示结束
def route_after_intent(state: AgentState):
    last_msg = state["messages"][-1].content.strip()
    logger.debug(f"The content of {last_msg}")
    if "1" in last_msg:
        return "tool_node"
    else:
        return "chat_node"


# 构建并编译图
def build_simple_graph():
    # 初始化状态图
    workflow = StateGraph(AgentState)

    # add_node传递自定义节点名和对应函数
    workflow.add_node("intent_classify", intent_classify_node)
    workflow.add_node("chat_node", chat_node)
    workflow.add_node("tool_node", tool_node)

    # 定义边：起点:第一个节点
    workflow.add_edge(START, "intent_classify")

    # 定义条件边：意图分类后分流
    workflow.add_conditional_edges(
        "intent_classify",
        route_after_intent,
        {"chat_node": "chat_node", "tool_node":"tool_node"}
    )

    # add_edge方法中的node都是之前定义的自定义节点名
    workflow.add_edge("chat_node", END)
    workflow.add_edge("tool_node", END)

    return workflow.compile()

if __name__ == "__main__":
    import asyncio
    graph = build_simple_graph()

    result = asyncio.run(graph.ainvoke({
        "messages": [HumanMessage(content="你好，今天天气怎么样？")]
    }))
    logger.info("图执行完成", final_answer=result["messages"][-1].content)