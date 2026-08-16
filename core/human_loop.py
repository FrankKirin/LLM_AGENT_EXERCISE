import asyncio
from core.config import settings
from typing import TypedDict, Annotated
import operator
from langchain.messages import AnyMessage, AIMessage, ToolMessage, HumanMessage
from rich import print
from core.lc_baseline import llm
from langgraph.graph import START, END, StateGraph
from langgraph.checkpoint.memory import MemorySaver


class HumanLoopState(TypedDict):
    messages: Annotated[list[AnyMessage], operator.add]
    task: str
    approval_status: str    # pending / approved / rejected
    human_feedback: str
    final_result: str

async def task_execute_node(state: HumanLoopState):
    prompt = f"""
    请完成以下任务：
    {state['task']}

    注意：这是初步方案，后续可能需要人工审核调整。
"""
    response = await llm.ainvoke(prompt)

    return {
        "final_result": response.content,
        "approval_status": "pending",
        "messages": [AIMessage(content="初步方案已生成，等待人工审核")]
    }

# 这个节点本身不做实质处理，作用是：
# 1.作为中断点的锚点
# 2.记录审核开始事件
# 3.加一些前置校验逻辑
def human_review_node(state: HumanLoopState):
    return {}

async def adjust_with_feedback_node(state: HumanLoopState):
    if state["approval_status"] == "approved":
        return {"messages": [AIMessage(content="审核通过，方案已确认")]}

    if state["approval_status"] == "rejected":
        prompt = f"""
        原始任务: {state['task']}

        当前方案: {state['final_result']}

        人工审核意见: {state['human_feedback']}

        请根据人工反馈修改方案，输出修改后的完整版本
        """
        response = await llm.ainvoke(prompt)

        return {
            "final_result": response.content,
            "approval_status": "pending",
            "messages": [AIMessage(content="已根据人工反馈调整方案，请重新审核")]
        }

    return {}

def route_after_review(state: HumanLoopState):
    if state["approval_status"] == "approved":
        return END
    if state["approval_status"] == "rejected":
        return "adjust"
    return END

def build_human_loop_graph():
    workflow = StateGraph(HumanLoopState)

    workflow.add_node("execute", task_execute_node)
    workflow.add_node("human_review", human_review_node)
    workflow.add_node("adjust", adjust_with_feedback_node)

    workflow.add_edge(START, "execute")
    workflow.add_edge("execute", "human_review")

    workflow.add_conditional_edges(
        "human_review",
        route_after_review,
        ["adjust", END]     # langgraph提供的语法糖
    )

    workflow.add_edge("adjust", "human_review")

    checkpointer = MemorySaver()

    return workflow.compile(
        checkpointer=checkpointer,
        interrupt_before=["human_review"]   # human review之前中断，强行暂停，等待外部干预
    )

async def human_approve(graph, config, feedback: str=""):
    """人工审核通过"""
    graph.update_state(
        config,
        {"approval_status": "approved", "human_feedback": feedback}
    )   # 修改checkpoint中的状态
    # 传入None表示无需传入新的初始数据，直接读取当前checkpoint暂存的状态
    result = await graph.ainvoke(None, config=config)
    return result

async def human_reject(graph, config, feedback: str):
    """人工审核驳回"""
    graph.update_state(
        config,
        {"approval_status": "rejected", "human_feedback": feedback}
    )
    # None表示从checkpoint恢复当前流程
    result = await graph.ainvoke(None, config=config)
    return result

async def test_approve_flow():
    config = {"configurable": {"thread_id": "approve_test_001"}}

    task = "请写一份关于AI Agent技术的项目立项方案"

    result = await graph.ainvoke(
        {
            "messages": [HumanMessage(content=task)],
            "task": task,
            "approval_status": "",
            "human_feedback": "",
            "final_result": ""
        },
        config=config
    )

    assert result["approval_status"] == "pending", "应该处于待审核状态"

    final_result = await human_approve(graph, config, "方案不错，同意通过")

    return final_result

# 超时控制
async def execute_with_timeout(task_coro, timeout_seconds: int=30):
    pass

# 权限控制
# WORKER_PERMISSIONS： 通过Role和worker name来控制权限，字典：worker名称：role列表
# 权限校验函数，返回bool表示是否有权限
# - 支持多role角色
WORKER_PERMISSIONS: dict[str, list[str]] = {
    "research_worker": ["user", "admin"],
    "analysis_worker": ["admin"],
    "report_worker": ["user", "admin"],
}

def check_worker_permission(worker_name: str, user_roles: list[str]) -> bool:
    for role in user_roles:
        if role in WORKER_PERMISSIONS.get(worker_name, []):
            return True

    return False


# 调用计数与限流
class RateLimiter:
    pass


if __name__ == "__main__":
    graph = build_human_loop_graph()
    print("="*25 + "打印mermaid图" + "="*25)
    print(graph.get_graph().draw_mermaid())

    approve_flow_res = test_approve_flow()
    print(approve_flow_res)

   