from langgraph.graph import StateGraph, START, END
from langgraph.runtime import Runtime
from arch_design.api_usage_subgraph.base_data import APIUsageState, AppContext
from core.lc_baseline import llm
from langchain.messages import SystemMessage, HumanMessage
from langgraph.prebuilt import ToolNode
import json
from langchain.tools import tool

MAX_TOOL_CALLS = 8
MAX_SAME_ACTION_ROUNDS = 3

def query_api_usage(state: APIUsageState, runtime: Runtime[AppContext]):
    """
        输入：state和runtime, 查询指定日期范围内的数据 
    """
    tenant_id = runtime.context["tenant_id"]

    print(
        f"\n[API Usage] 查询租户 {tenant_id} "
        f"的调用数据：{state['start_date']} ~ {state['end_date']}"
    )

    # 模拟 SQL 查询结果，不是真实业务数据
    rows = [
        {"date": "2026-10-05", "calls": 1000},
        {"date": "2026-10-06", "calls": 1200},
        {"date": "2026-10-07", "calls": 1300},
        {"date": "2026-10-08", "calls": 1400},
        {"date": "2026-10-09", "calls": 1500},
        {"date": "2026-10-10", "calls": 1500},
        {"date": "2026-10-11", "calls": 9200},
    ]

    # 输出：写入子图的 State Update
    return {
        "api_result": rows
    }

def detect_anomaly(state: APIUsageState):
    rows = state["api_result"]

    previous_calls = [row["calls"] for row in rows[:-1]] # 不处理列表最后一个元素

    latest_calls = rows[-1]["calls"]

    average_calls = sum(previous_calls) / len(previous_calls)
    anomaly = latest_calls > average_calls * 3

    print(
        f"[API Usage] 前六天平均调用量：{average_calls:.0f}，"
        f"最近一天：{latest_calls}，异常：{anomaly}"
    )

    return {
        "anomaly_detected": anomaly
    }

def route_after_detection(state: APIUsageState):
    if state["anomaly_detected"]:
        return "investigate"

    return "normal"

def prepare_investigation(state: APIUsageState):
    rows = state["api_result"]

    task = (
        f"用户问题：{state['user_query']}\n"
        f"查询范围：{state['start_date']} 至 {state['end_date']}\n"
        f"API 调用记录：{rows}\n"
        f"异常标记：{state['anomaly_detected']}\n"
        "请调查异常可能原因。必须分别调用历史记录查询工具和 "
        "RAG 工具，结合返回的证据分析，不要把可能原因当成已证实事实。"
    )

    return {
        "messages": [HumanMessage(content=task)]
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
            "历史记录：需要核实异常时段是否存在批量任务"
            "或特定调用方的请求激增。"
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

def investigator_llm(state: APIUsageState):
    system_message = SystemMessage(
        content=("你是API Usage异常分析Agent, "
                 "你可以调用工具搜集证据。收集到工具结果后，"
                 "判断信息是否足够，如果足够，输出简洁的分析结论；"
                 "如果不够，继续调用合适的工具。不得将未经证实的假设描述为事实。"
            )
    )
    
    response = investigator_model.invoke(
        [
            system_message,
            *state["messages"],
        ]
    )

    print("\n[LLM] 本轮输出：")
    print(response.content)
    print("[LLM] Tool Calls：", response.tool_calls)

    return {
        "messages": [response],
    }

def analyze_causes(state: APIUsageState):
    rows = state["api_result"]
    latest = rows[-1]["calls"]

    # 前6天平均
    average = sum(row["calls"] for row in rows[:-1]) / len(rows[:-1])

    causes = [
        (   f"最近一天调用量为 {latest}，"
            f"前六天平均值约为 {average:.0f}，存在明显峰值。"
        ),
        state["history_result"],
        state["rag_result"],
    ]

    print("[API Usage]已整理异常分析结果")

    return {
        "possible_causes": causes
    }

# Loop Guard节点，做执行前检查
def guard_tool_calls(state: APIUsageState):
    last_message = state["messages"][-1]
    tool_calls = last_message.tool_calls

    if not tool_calls:
        return {}

    # 比较工具名称和参数，不比较每轮变化的tool_call_id, tool_calls通常是个list，每个call都需要处理
    # name和args相同算签名相同
    normalized_calls = [{
        "name": call["name"],
        "args": call.get("args", {}),
    } for call in tool_calls]

    signature = json.dumps(
        normalized_calls,
        sort_keys=True,
        ensure_ascii=False,
        default=str,
    )

    previous_signature = state["last_action_signature"]

    # 签名只和上一轮签名比较，相同计数+1；不同将签名计数设置为1
    if signature == previous_signature:
        same_count = state["same_action_count"] + 1
    else:
        same_count = 1

    # 总调用数
    total_calls = state["tool_call_count"] + len(tool_calls)

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

# 新的子图
api_builder = StateGraph(APIUsageState, context_schema=AppContext)

# 添加节点
api_builder.add_node("query_api_usage", query_api_usage)
api_builder.add_node("detect_anomaly", detect_anomaly)
api_builder.add_node("prepare_investigation", prepare_investigation)
api_builder.add_node("investigator_llm", investigator_llm)
# ToolNode会接收大模型发出的工具调用请求，并实际执行，然后返回执行结果
api_builder.add_node("investigation_tools", ToolNode(investigation_tools, handle_tool_errors=True))
api_builder.add_node("finish_investigation", finish_investigation)
api_builder.add_node("guard_tool_calls", guard_tool_calls)
api_builder.add_node("loop_guard_stop", loop_guard_stop)

api_builder.add_edge(START, "query_api_usage")
api_builder.add_edge("query_api_usage", "detect_anomaly")

api_builder.add_conditional_edges(
    "detect_anomaly",
    route_after_detection,
    {
        "investigate": "prepare_investigation",
        "normal": END
    }
)

# Agent Loop
api_builder.add_edge(
    "prepare_investigation",
    "investigator_llm",
)

api_builder.add_conditional_edges(
    "investigator_llm",
    route_investigation,
    {
        "guard_tool_calls": "guard_tool_calls",
        "finish_investigation": "finish_investigation",
    }
)

api_builder.add_conditional_edges(
    "guard_tool_calls",
    route_after_guard,
    {
        "investigation_tools": "investigation_tools",
        "loop_guard_stop": "loop_guard_stop",
    }
)

api_builder.add_edge(
    "investigation_tools",
    "investigator_llm",
)

api_builder.add_edge(
    "loop_guard_stop",
    END,
)

api_usage_graph = api_builder.compile()
print("api_usage_graph图\n")
print(api_usage_graph.get_graph().draw_mermaid())
print("\n")

res = api_usage_graph.invoke({
    # 自动累加的历史消息记录
    "messages":[],
    "user_query": "",
    "start_date": "2026-10-05",
    "end_date": "2026-10-11",
    "api_result": [],
    "anomaly_detected": False,
    "history_result":"", # 历史日志
    "rag_result": "",
    # 子图分析过程
    "possible_causes": [],
    "tool_call_count": 0,
    "last_action_signature": "",
    "same_action_count": 0,
    "loop_guard_triggered": False,
    "stop_reason": "",
},

{
    "recursion_limit": 25 # Graph级别的保险
},
    context=AppContext(tenant_id="BYD", session_id="001", user_id="BYD_user01")
)

print(res["possible_causes"])

# 没有严格比较每次工具的实际返回内容

# 第一层：正常结束条件
#         ↓
# 第二层：Loop Guard 检查重复动作
#         ↓
# 第三层：recursion_limit 兜底