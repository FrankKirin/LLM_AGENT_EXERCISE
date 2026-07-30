# React: 思考->工具调用->结果观测->再思考->回答
import operator
from typing import Annotated, TypedDict, Literal
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage, AnyMessage
from core.lc_baseline import llm, tools
from core.logger import logger
from langgraph.graph import StateGraph, START, END

# 定义节点类
# 1.给字典加上IDE自动补全 2.告诉langgraph图的状态结构
class ReactState(TypedDict):
    messages: Annotated[list[AnyMessage], operator.add]
    call_num: int

# 创建好llm并绑定tools,并且需要改造成图节点
llm_with_tool = llm.bind_tools(tools)

def llm_tool(state: ReactState):
    messages = state["messages"]
    return {
        "messages": [llm_with_tool.invoke(messages)],
        "call_num": state.get("call_num", 0) + 1
    }

# 定义判断节点
def should_continue(state: ReactState)->Literal["tool_node", END]:
    messages = state["messages"][-1].content
    logger.debug("should continue节点最后messages内容", res=messages)
    tool_calls = state["messages"][-1].tool_calls
    logger.debug("should continue节点最后messages.tool_calls", res=tool_calls)
    if tool_calls:
        return "tool_node"
    return END

def tool_node(state: ReactState):
    # 执行函数，并将执行顺序绕回llm_tool
    tool_calls = state["messages"][-1].tool_calls
    logger.debug("打印查看最后一条完整message内容", content=state["messages"][-1])
    logger.debug("打印查看tool_calls内容", tool_calls=tool_calls)
    # tool_calls是个list包裹的字典，访问字典用dict["key_name"]
    tools_with_name = {tool.name:tool for tool in tools}
    print("*"*100)
    logger.debug(f"tools_with_name:{tools_with_name}")
    # 写成list是为了支持多工具并行调用，并且符合图节点返回类型必须为list的要求
    final_res = []
    for tool in tool_calls:
        logger.debug("打印tool_node中for循环tool的内容", tool=tool)
        func = tools_with_name[tool["name"]]
        res = func.invoke(tool["args"])
        final_res.append(res)

    logger.debug("tool_node函数中final_res结果为", final_res=final_res)

    return {"message": final_res}


# 构建graph方法
def build_graph():
    # 构造一个节点类型为ReactState的图
    agent_builder = StateGraph(ReactState)
    # llm调用节点和tool调用节点添加到图
    agent_builder.add_node("llm_tool", llm_tool)
    agent_builder.add_node("tool_node", tool_node)

    agent_builder.add_edge(START, "llm_tool")
    # agent_builder.add_edge("llm_call", "should_continue")
    agent_builder.add_conditional_edges(
        "llm_tool",
        should_continue,
        # 如果should_continue返回"tool_node"就走tool_node，否则就END
        ["tool_node", END]
    )

    return agent_builder.compile()

if __name__ == "__main__":
    # 实现异步调用
    import asyncio
    state = {"messages": [HumanMessage(content="工号C1001员工的信息")]}
    graph = build_graph()
    result = asyncio.run(graph.ainvoke(state))
    print(result)


    # state = {"messages": [HumanMessage(content="员工工号C1001的信息")]}
    # res = should_continue(state)

    # print(res)