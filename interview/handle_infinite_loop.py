from typing import TypedDict

from langgraph.graph import StateGraph, START, END


# =========================
# 1. 定义 State
# =========================

class AgentState(TypedDict):
    user_query: str
    step_count: int
    tool_history: list[str]
    answer: str


# =========================
# 2. 三个工具
# =========================

def tool_a(state: AgentState):
    print("🔧 Tool A 被调用")

    # 模拟工具自身发生异常
    try:
        print("   Tool A: 查询订单...")
        return {"answer": "订单查询成功"}

    except Exception as e:
        # Tool 自己处理自己的异常
        print(f"   Tool A 出错: {e}")
        return {"answer": "订单查询失败"}


def tool_b(state: AgentState):
    print("🔧 Tool B 被调用")

    try:
        print("   Tool B: 查询库存...")
        return {"answer": "库存查询成功"}

    except Exception as e:
        print(f"   Tool B 出错: {e}")
        return {"answer": "库存查询失败"}


def tool_c(state: AgentState):
    print("🔧 Tool C 被调用")

    try:
        print("   Tool C: 查询物流...")
        return {"answer": "物流查询成功"}

    except Exception as e:
        print(f"   Tool C 出错: {e}")
        return {"answer": "物流查询失败"}


# =========================
# 3. Agent 编排节点
# =========================

MAX_STEPS = 6


def supervisor(state: AgentState):
    """
    这里模拟 Agent 决策：
    A → B → C → A → B → C → ...
    故意制造死循环
    """

    # ---------- 第一层保护：最大执行次数 ----------
    if state["step_count"] >= MAX_STEPS:
        print("🚨 超过最大执行次数，强制停止 Agent")
        raise RuntimeError("Agent执行次数超过上限，疑似死循环")

    step = state["step_count"]

    # ---------- 第二层保护：重复调用检测 ----------
    history = state["tool_history"]

    if len(history) >= 2:
        # 最近两次一样，认为开始重复
        if history[-1] == history[-2]:
            print("🚨 检测到连续重复调用")
            raise RuntimeError("检测到 Agent 工具调用死循环")

    # 模拟 Agent 不断轮流调用工具
    tools = ["tool_a", "tool_b", "tool_c"]

    current_tool = tools[step % 3]

    print(f"\n🤖 Agent 第 {step + 1} 次决策：调用 {current_tool}")

    return {
        "step_count": step + 1,
        "tool_history": history + [current_tool],
    }


# =========================
# 4. 路由
# =========================

def route_tool(state: AgentState):

    last_tool = state["tool_history"][-1]

    if last_tool == "tool_a":
        return "tool_a"

    if last_tool == "tool_b":
        return "tool_b"

    if last_tool == "tool_c":
        return "tool_c"

    return "end"


# =========================
# 5. 构建 Graph
# =========================

graph_builder = StateGraph(AgentState)

graph_builder.add_node("supervisor", supervisor)
graph_builder.add_node("tool_a", tool_a)
graph_builder.add_node("tool_b", tool_b)
graph_builder.add_node("tool_c", tool_c)

graph_builder.add_edge(START, "supervisor")

graph_builder.add_conditional_edges(
    "supervisor",
    route_tool,
    {
        "tool_a": "tool_a",
        "tool_b": "tool_b",
        "tool_c": "tool_c",
        "end": END,
    }
)

# 三个 Tool 执行完以后，都重新回到 Supervisor
graph_builder.add_edge("tool_a", "supervisor")
graph_builder.add_edge("tool_b", "supervisor")
graph_builder.add_edge("tool_c", "supervisor")

graph = graph_builder.compile()
print(graph.get_graph().draw_mermaid())


# =========================
# 6. 执行
# =========================

try:
    result = graph.invoke({
        "user_query": "帮我查询一下订单",
        "step_count": 0,
        "tool_history": [],
        "answer": "",
    })

    print("\n最终结果：")
    print(result)

except Exception as e:
    print("\n💥 Agent 被系统保护机制终止：")
    print(e)