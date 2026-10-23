from langgraph.types import Command
from langgraph.graph import END, START, StateGraph
from langgraph.runtime import Runtime
from arch_design.supervisor_subgraph.base_data import ParentState, AppContext, APIUsageState, APIUsageReport, observe_node
from arch_design.supervisor_subgraph.sub_graph import api_usage_graph

# supervisor动态选择下一步
def supervisor(state: ParentState) -> Command:
    # 第一次到达：尚未运行API Usage
    if state["api_status"] == "pending":
        print("\n[Supervisor]委托API Usage专家执行任务")
        return Command(
            update={"activate_agent": "api_usage"},
            goto="run_api_usage"
        )
    # 子图完成后，再次进入Supervisor
    if state["api_status"] == "completed":
        print("[Supervisor]已收到结果，准备生成最终总结")
        return Command(
            update={"active_agent": "supervisor"},
            goto="summarize",
        )
    return Command(goto=END)

# 调用子图, 接收结果时，再做一次边界校验
def run_api_usage(state: ParentState, runtime: Runtime[AppContext]):
    # 父图数据映射后给到子图作为输入
    child_input: APIUsageState = {
        "user_query": state["user_query"],
        "start_date": state["start_date"],
        "end_date": state["end_date"],
        "anomaly_detected": False,
        "messages": [],
        "api_result": [],
        "history_result": "",
        "rag_result": "",

        "ok": True,
        "error_code": "",
        "message": "",

        "tool_signature_counts": {},
        "api_usage_report": {},
        "tool_rounds": 0,
        "loop_blocked": False, 
        "loop_guard_triggered": False, 
        "stop_reason": "",
        "possible_causes": [],
        "report_repair_count": 3,
    }

    child_result = api_usage_graph.invoke(
        child_input,
        context=runtime.context,
    )

    print(f"The content of api_usage_report: {child_result['api_usage_report']}")

    report = APIUsageReport.model_validate(
        child_result["api_usage_report"]
    )

    return {
        "api_status": "completed",
        "api_usage_report": report.model_dump(mode="json")  # pydantic对象转dict
    }
  
def summarize(state: ParentState):
    report = APIUsageReport.model_validate(
        state["api_usage_report"]
    )
    # 根据report传回的状态分别处理
    if report.status == "completed":
        answer = report
    elif report.status == "failed":
        answer = "API使用情况分析失败，暂时无法给出结论"
    elif report.status == "insufficient_data":
        answer = (
            "当前证据不足，无法可靠判断是否存在异常"
            f"趋势分析：{report.trend_summary}"      
        )
    elif report.anomaly_detected is False:
        answer = (
            "在当前数据和判断规则下，未检测到明显异常。"
            f"趋势分析：{report.trend_summary}"
        )
    else:
        answer = "分析已返回，但异常判断尚不明确。"

    print(f"Summarize节点的answer{answer}")

    return {"final_answer": answer}

# 构建图
parent_builder = StateGraph(ParentState, context_schema=AppContext)

parent_builder.add_node("supervisor", supervisor)
parent_builder.add_node("run_api_usage", run_api_usage)
parent_builder.add_node("summarize", summarize)

parent_builder.add_edge(START, "supervisor")  # supervisor下一步由Command的goto决定
parent_builder.add_edge("run_api_usage", "supervisor") 
parent_builder.add_edge("summarize", END)

parent_graph = parent_builder.compile()

print("pareent_graph的样子：")
print(parent_graph.get_graph().draw_mermaid())

print("用stream方法来观察结果:\n")
result = parent_graph.invoke(
    {
        "user_query": "查询最近 7 天 API 调用趋势，如果异常就分析原因",
        "start_date": "2026-10-05",
        "end_date": "2026-10-11",

        "api_status": "pending",
        "active_agent": "supervisor",
        "api_result": [],
        "anomaly_detected": False,
        "possible_causes": [],
        "api_usage_report": {},
        "final_answer": "",
    },
    context={
        "tenant_id": "tenant_demo_001",
        "user_id": "user_demo_001",
        "session_id": "session_demo_001",
    },
    config={
        "recursion_limit": 25,
    },
    # stream_mode="updates"
)

print("\n========== 最终结果 ==========")
print(result["final_answer"])