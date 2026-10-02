from typing_extensions import TypedDict

from langgraph.graph import StateGraph, START, END
from langgraph.types import Command


class State(TypedDict):
    user_query: str
    current_agent: str
    result: str

# ========================================
# Support
# ========================================

def support(state: State):

    query = state["user_query"]

    if "退款" in query:
        print("\n[Support] → 转交 AfterSales")

        return Command(
            goto="after_sales",
            # current_agent是图节点的一个参数
            update={
                "current_agent": "after_sales"
            }
        )

    if "购买" in query or "价格" in query:
        print("\n[Support] → 转交 Sales")

        return Command(
            goto="sales",
            update={
                "current_agent": "sales"
            }
        )

    return Command(
        goto=END,
        update={
            "result": "Support 直接处理"
        }
    )

# ========================================
# Sales
# ========================================

def sales(state: State):

    print("\n[Sales] 当前负责处理")

    return {
        "result": "Sales：我们的产品售价 999 元"
    }

# ========================================
# After Sales
# ========================================

def after_sales(state: State):

    print("\n[AfterSales] 当前负责处理")

    return {
        "result": "AfterSales：您的退款申请已受理"
    }

# ========================================
# Graph
# ========================================

builder = StateGraph(State)

builder.add_node("support", support)
builder.add_node("sales", sales)
builder.add_node("after_sales", after_sales)

builder.add_edge(START, "support")

builder.add_edge("sales", END)
builder.add_edge("after_sales", END)

graph = builder.compile()
print(graph.get_graph().draw_mermaid())

result = graph.invoke({
    "user_query": "我想购买这个产品",
    "current_agent": "support",
    "result": "",
})
