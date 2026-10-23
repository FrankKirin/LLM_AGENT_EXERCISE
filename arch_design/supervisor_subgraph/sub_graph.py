from langgraph.graph import StateGraph, START, END
from langgraph.runtime import Runtime
from arch_design.supervisor_subgraph.base_data import APIUsageState, AppContext, APIUsageReport, observe_node
from core.lc_baseline import llm
from langchain.messages import SystemMessage, HumanMessage, AIMessage
from langgraph.prebuilt import ToolNode
import json
from langchain.tools import tool
from langgraph.types import RetryPolicy
from sqlalchemy.exc import OperationalError
from pydantic import ValidationError

MAX_TOOL_CALLS = 8
MAX_SAME_ACTION_ROUNDS = 3

def seed_user_query(state: APIUsageState):
    if state.get("messages"):
        return {}
    return {"messages": [HumanMessage(content=state["user_query"])]}

def query_with_retry(tenant_id: str, start_date: str, end_date: str):
    pass

@observe_node("query_api_usage")
def query_api_usage(state: APIUsageState):
    """查询指定日期范围内的API调用记录"""
    try:
        rows = [
            {"date": "2026-10-05", "calls": 1000},
            {"date": "2026-10-06", "calls": 1200},
            {"date": "2026-10-07", "calls": 1300},
            {"date": "2026-10-08", "calls": 1400},
            {"date": "2026-10-09", "calls": 1500},
            {"date": "2026-10-10", "calls": 1500},
            {"date": "2026-10-11", "calls": 9200},
        ]
        return {"api_result": rows}
    except (OperationalError, TimeoutError) as e:
        # 只处理可以明确是别的可预期错误(瞬态错误)
        # 不把所有Exception都吞掉
        print(f"[API Usage] 查询失败: {e}")
        return {
            "api_result": [],
            "stop_reason": f"查询失败: {type(e).__name__}"
        }

def finish_investigation(state: APIUsageState):
    last_message = state["messages"][-1]

    answer = str(last_message.content).strip()

    return {
        "possible_causes": [answer] if answer else []
    }

# 查询历史记录和知识库
@tool
def lookup_history(start_date: str, end_date: str):
    """查询指定日期范围内的历史API调用记录。"""
    print("[API Usage] 查询历史调用记录")

    # 模拟历史数据查询
    return {
        "history_result": (
            "历史记录：国庆旅游季访问量激增"
        )
    }

@tool
def retrieve_rag(state: APIUsageState):
    """从知识库检索API异常和流量激增的相关资料"""
    print("[API Usage] 检索知识库")

    return {
       "rag_result": (
            "知识库资料：不合理的自动重试、缺少退避机制"
            "或调用方循环请求，都可能放大 API 流量。"
        )
    }

investigation_tools = [lookup_history, retrieve_rag]

# 把工具的名称
investigator_model = llm.bind_tools(investigation_tools)

# def stub_investigator_llm(state: APIUsageState):
#     tc = [{
#         "name":"tool_HISTORY_RAG",
#         "args": {"start_date": state["start_date"], "end_date": state["end_date"]},
#         "id": "call_duplicate",
#         "type": "tool_call",
#     }]

#     return {
#         "messages": [AIMessage(content="", tool_calls=tc)]
#     }

def investigator_llm(state: APIUsageState):
    system_message = SystemMessage(
        content = f"""
            你是API使用情况分析分析Agent,
            需要根据用户问题和日期范围查询数据, 必要时查询历史基线，在分析是否异常
            判断信息是否足够，如果足够，输出简洁的分析结论；
            如果不够，继续调用合适的工具。不得将未经证实的假设描述为事实。
            本次分析日期范围:{state['start_date'], {state['end_date']}}

            根据工具返回数据和分析结果，只要一个JSON对象, 不要其他文字
            必须包含：
            status: "completed", "insufficient_data", "failed"
            start_date: str
            end_date: str
            anomaly_detected: bool | None
            trend_summary: str = ""
            possible_causes: list[str]
            limitations: list[str]
            error_code: str | None

            要求：
            1. 不得编造工具未提供的事实。
            2. 证据不足时，anomaly_detected 必须为 null。
            3. possible_causes 必须是数组。
            4. 只输出 JSON，不要添加 Markdown 代码围栏。
            例如：
            {{
            "status": "completed",
            "start_date": "2026-10-01",
            "end_date": "2026-10-22",
            "anomaly_detected": false,
            "trend_summary": "整体指标平稳，未发现显著异常波动。",
            "possible_causes": [],
            "limitations": [
                "数据仅覆盖近30天，历史基线不足。"
            ],
            "error_code": null
            }}
        """
 
    )

    response = investigator_model.invoke(
        [
            system_message,
            *state["messages"],
        ]
    )

    print("\n[LLM] 本轮输出：")
    print(response.content)
    print("[LLM] Tool Calls调用内容：", response.tool_calls)

    return {
        "messages": [response],
    }

# 构建api_usage_report
def build_api_usage_report(state):
    # 按照APIUsageReport数据要求生成APIUsageReport
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
    # rows内容为空的情况
    else:
        causes = [
            cause for cause in state["possible_causes"]
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

# Loop Guard节点，做执行前检查
def guard_tool_calls(state: APIUsageState):
    last_message = state["messages"][-1]
    tool_calls = last_message.tool_calls

    if not tool_calls:
        return {}

    # 比较工具名称和参数，不比较每轮变化的tool_call_id, tool_calls通常是个list，每个call都需要处理
    # name和args相同算签名相同
    normalized_calls = [{"name": call["name"], "args": call.get("args", {}),} for call in tool_calls]

    signature = json.dumps(
        normalized_calls,
        sort_keys=True,
        ensure_ascii=False,
        default=str,
    )

    # previous_signature = state["tool_signature_counts"].get("signature", 0)

    # 签名只和上一轮签名比较，相同计数+1；不同将签名计数设置为1
    # 添加到tool_signature_counts，数量+1
    same_count = 0
    if state["tool_signature_counts"].get(signature):
        state["tool_signature_counts"][signature] += 1
    else:
        state["tool_signature_counts"][signature] = 1
    same_count = state["tool_signature_counts"][signature]

    # 总调用数
    total_calls = sum(state["tool_signature_counts"].values())

    # 相同参数、函数调用轮次超出或者总调用次数超过最大工具调用次数
    should_stop = (same_count >= MAX_SAME_ACTION_ROUNDS or total_calls > MAX_TOOL_CALLS)

    reason = ""
    if same_count >= MAX_SAME_ACTION_ROUNDS:
        reason = "连续重复相同工具调用，未发现有效进展"
    elif total_calls > MAX_TOOL_CALLS:
        reason = "工具调用总数超过限制"

    return {
        "last_action_signature": signature,
        "same_action_count": same_count,
        "tool_call_count": total_calls,
        "loop_guard_triggered": should_stop,
        "stop_reason": reason,
    }

def route_investigation(state: APIUsageState):
    last_message = state["messages"][-1]

    if last_message.tool_calls:
        return "guard_tool_calls"

    return "finish_investigation"

def route_after_guard(state: APIUsageState):
    if state["loop_guard_triggered"]:
        return "loop_guard_stop"

    return "investigation_tools"

def loop_guard_stop(state: APIUsageState):
    message = ("异常调查已提前停止："
               f"{state['stop_reason']}。"            
               "请检查工具结果与调查策略，避免重复无效操作。"
    )

    return {
        "possible_causes": [message]
    }

# loop_guard_stop改进版
def force_report(state: APIUsageState):
    report = APIUsageReport(
        status="insufficient_data",
        start_date=state["start_date"],
        end_date=state["end_date"],
        anomaly_detected=None,
        trend_summary="调查未能在允许的工具调用轮次内完成。",
        limitations=["触发工具调用轮次上限，未完成完整分析。"]
    )

    return {"api_usage_report": report.model_dump(mode="json")}

def parse_report(state: APIUsageState):
    last_message = state["messages"][-1]

    try:
        # Json能否解析，字段类型是否正确，必填字段是否存在
        payload = json.loads(last_message.content) # str to obj
        # 即使结构正确，字段间关系是否符合规定的业务契约
        report = APIUsageReport.model_validate(payload)
    except (json.JSONDecodeError, ValidationError) as e:
        print(e)
        
        report = APIUsageReport(
            status = "failed",
            start_date = state["start_date"],
            end_date = state["end_date"],
            anomaly_detected=None,
            trend_summary="无法解析或校验Agent的最终报告。",
            limitations=["最终输出不符合报告格式。"],
            error_code="INVALID_REPORT",
            # 完整：确保investigator_llm准备生成最终报告时收到REPORT_PROMPT, 限制报告修复次数
        )

    return {
        'api_usage_report': report,
    }

def finalize_failed(state: dict)->dict:
    # 符合APIUsageReport的输出结构
    # 不会因为查询失败，假装已经得出没有异常的结论
    # error_code可以帮助父图或监控系统判断失败类型
    # 父图不必了解子图内部究竟运行了多少轮ReAct循环
    report = APIUsageReport(
        status="failed",
        start_date=state["start_date"],
        end_date=state["end_date"],
        anomaly_detected=None,
        trend_summary="",
        possible_causes=[],
        limitations=["本次分析未能成功完成，不能据此判断是否存在异常"],
        error_code=(
            "LOOP_GUARD" if state.get("loop_guard_triggered") else "ANALYSIS_FAILED"
        ),
    )
    return {
        "report": report.model_dump(mode="json")
    }

# 新的子图
api_builder = StateGraph(APIUsageState, context_schema=AppContext)

# 添加节点
# 第二层错误处理
api_builder.add_node("seed_user_query", seed_user_query)
api_builder.add_node("query_api_usage", query_api_usage)
api_builder.add_node(
    "investigator_llm", 
    investigator_llm, 
    retry_policy=RetryPolicy(
        max_attempts=3,
        retry_on=(TimeoutError, ConnectionError), # 符合retry_on的异常，最多尝试3次，包括第一次执行
    )
)
# ToolNode会接收大模型发出的工具调用请求，并实际执行，然后返回执行结果
api_builder.add_node("investigation_tools", ToolNode(investigation_tools, handle_tool_errors=True))
api_builder.add_node("finish_investigation", finish_investigation)
api_builder.add_node("guard_tool_calls", guard_tool_calls)
api_builder.add_node("loop_guard_stop", loop_guard_stop)
api_builder.add_node("force_report", force_report)
api_builder.add_node("parse_report", parse_report)

api_builder.add_edge(START, "seed_user_query")
api_builder.add_edge("seed_user_query", "query_api_usage")

api_builder.add_edge(
    "query_api_usage",
    "investigator_llm",
)
api_builder.add_conditional_edges(
    "investigator_llm",
    route_investigation,
    {
        "guard_tool_calls": "guard_tool_calls",
        "finish_investigation": "parse_report",
    }
)

api_builder.add_conditional_edges(
    "guard_tool_calls",
    route_after_guard,
    {
        "investigation_tools": "investigation_tools",
        "loop_guard_stop": "force_report",
    }
)

api_builder.add_edge(
    "investigation_tools",
    "investigator_llm",
)

api_builder.add_edge(
    "investigation_tools",
    "loop_guard_stop",
)

api_builder.add_edge(
    "parse_report",
    END,
)

api_builder.add_edge(
    "force_report",
    END,
)

api_usage_graph = api_builder.compile()
# print("api_usage_graph图\n")
# print(api_usage_graph.get_graph().draw_mermaid())
# print("\n")

# res = api_usage_graph.invoke({
#     # 自动累加的历史消息记录
#     "user_query": "查询最近 7 天 API 调用趋势，如果异常就分析原因", 
#     "start_date": "2026-10-05",
#     "end_date": "2026-10-11",

#     "api_result": [],
#     "anomaly_detected": False,
#     "messages":[],

#     "history_result":"",
#     "rag_result": "",

#     # 子图分析过程
#     "tool_signature_counts":{},
#     "api_usage_report":{},
#     "tool_rounds": 0,
#     "loop_blocked":False,
#     "loop_guard_triggered": False,
#     "stop_reason": "",
#     "possible_causes": "",
# },

# {
#     "recursion_limit": 10 # Graph级别的保险
# },
#     context=AppContext(tenant_id="BYD", session_id="001", user_id="BYD_user01")
# )

# print(res["possible_causes"])

# 没有严格比较每次工具的实际返回内容

# 第一层：正常结束条件
#         ↓
# 第二层：Loop Guard 检查重复动作
#         ↓
# 第三层：recursion_limit 兜底

# API Usage Agent的故障处理
# 1.工具执行：可识别的错误；未预期的错误暴露出来, 配合retry_policy
# 2.Agent Loop, Loop Guard限制重复调用；进展判断避免工具重复执行却不产生新信息
# 3.结果校验：JSON解析、Pydantic校验、业务语义校验、有限修复
# 4.结果契约；子图输出completed、insufficient_date或failed；父图只消费经过校验的业务结果