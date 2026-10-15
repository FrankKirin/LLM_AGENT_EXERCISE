from langgraph.types import Command
from langgraph.graph import END, START, StateGraph
from langgraph.runtime import Runtime
from arch_design.api_usage_subgraph.base_data import ParentState, AppContext, APIUsageState, APIUsageReport, CauseEvidence
from arch_design.api_usage_subgraph.sub_graph import api_usage_graph

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

def build_api_usage_report(state):
    rows = state["api_result"]

    if not rows:
        report = APIUsageReport(
            status="insufficient_data",
            start_date=state["start_date"],
            end_date=state["end_date"],
            anomaly_detected=None,
            trend_summary="没有获得足够的API调用记录",
            limitations=["无法基于现有数据判断调用趋势"],
        )
    else:
        causes = [
            CauseEvidence(
                cause=cause,
                evidence=[],
                confidence="low",
                need_verification=True,
            )
            for cause in state["possible_causes"]
        ]
        report  = APIUsageReport(
            status="completed",
            start_date=state["start_date"],
            end_date=state["end_date"],
            anomaly_detected=state["anomaly_detected"],
            trend_summary="已完成指定日期范围内的API调用分析",
            possible_causes=causes,
            limitations=(
                [] if not state["anomaly_detected"] else ["可能原因仍需结合真实日志验证"]
            ),
        )
    return {
        "api_usage_report": report.model_dump(mode="json")
    }

# 调用子图, 接收结果时，再做一次边界校验
def run_api_usage(state: ParentState, runtime: Runtime[AppContext]):
    # 父图传给子图的字段映射到子图输入
    child_input: APIUsageState = {
        "user_query": state["user_query"],
        "start_date": state["start_date"],
        "end_date": state["end_date"],
        "api_result": [],
        "anomaly_detected": False,
        "history_result": "",
        "rag_result": "",
        "possible_causes": [],
    }

    child_result = api_usage_graph.invoke(
        child_input,
        context=runtime.context,
    )

    report = APIUsageReport.model_validate(
        child_result["api_usage_report"]
    )

# 父图对子图返回的report验证后处理结果
def route_after_api_usage(state):
    report = APIUsageReport.model_validate(
        state["api_usage_report"]
    )
    if report.status == "failed":
        return "handle_failure"

    if report.status == "insufficient_data":
        return "request_more_data"

    if report.anomaly_detected:
        return "summarize_anomaly"

    return "summarize_normal"

def summarize(state: ParentState):
    rows = state["api_result"]

    latest = rows[-1]["calls"]
    average = sum(row["calls"] for row in rows[:-1]) / len(rows[:-1])

    if state["anomaly_detected"]:
        causes_text = "\n".join(
            f"- {cause}"
            for cause in state["possible_causes"]
        )

        answer = (
            f"最近 7 天 API 调用存在异常。"
            f"最近一天调用量为 {latest}，"
            f"前六天平均约为 {average:.0f}。\n"
            f"可能原因及待核查线索：\n{causes_text}"
        )
    else:
        answer = (
            f"最近 7 天 API 调用总体未触发当前异常规则。"
            f"最近一天调用量为 {latest}，"
            f"前六天平均约为 {average:.0f}。"
        )

    return {
        "final_answer": answer
    }

parent_builder = StateGraph(ParentState, context_schema=AppContext)

parent_builder.add_node("supervisor", supervisor)
parent_builder.add_node("run_api_usage", run_api_usage)
parent_builder.add_node("summarize", summarize)

parent_builder.add_edge(START, "supervisor")  # supervisor下一步由Command的goto决定
parent_builder.add_edge("run_api_usage", "supervisor")  # 通过固定Edge返回Supervisor
parent_builder.add_edge("summarize", END)

parent_graph = parent_builder.compile()

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
)

print("\n========== 最终结果 ==========")
print(result["final_answer"])