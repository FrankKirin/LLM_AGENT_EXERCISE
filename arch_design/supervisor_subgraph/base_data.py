# from typing import TypedDict, Any, Annotated # python 3.12后大胆用这个
import logging, time, inspect
from functools import wraps
from typing_extensions import TypedDict, Any, Annotated, Literal # python多版本兼容用这个
from pydantic import BaseModel, Field
from langgraph.graph.message import add_messages

# 类用来传递上下文
class AppContext(TypedDict):
    tenant_id: str
    user_id: str | None
    session_id: str | None

class ParentInput(TypedDict):
    user_query: str
    start_date: str
    end_date: str

# 父Agent的state定义
class ParentState(TypedDict):   # 静态标注
    user_query: str
    start_date: str
    end_date: str
    # pending; completed; insufficient_data
    api_status: str
    active_agent: str
    api_result: list[dict[str, Any]]    

    anomaly_detected: bool  # 是否检测到异常
    possible_causes: list[str] # 异常可能原因

    api_usage_report: dict
    final_answer: str

# Sub-Agent内部单独State定义
class APIUsageState(TypedDict):
    user_query: str
    start_date: str
    end_date: str

    anomaly_detected: bool

    # 自动累加的历史消息记录
    messages: Annotated[list, add_messages]
    api_result: list[dict[str, Any]] # 原始查询数据

    # 历史日志与rag查询结果
    history_result: str
    rag_result: str

    # Loop Guard，循环监控
    tool_signature_counts: dict[str, int]

    api_usage_report: dict[str, Any]

    tool_rounds: int  # 控制工具调用循环
    loop_blocked: bool

    ok: bool
    error_code: Literal["INVALID_DATE_RANGE", ""]
    message: str

    report_repair_count: int  # 控制报告解析错误调用循环

    loop_guard_triggered: bool
    stop_reason: str
    possible_causes: list[str]

# 父图最终需要的一份语义明确的报告
class APIUsageReport(BaseModel):
    # 整个分析任务状态
    status: Literal["completed", "insufficient_data", "failed"]
    start_date: str
    end_date: str

    # 分析业务结论
    anomaly_detected: bool | None = None

    trend_summary: str = ""
    possible_causes: list[str] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)  # 分析的限制
    error_code: str | None = None  # 失败时用于定位的错误类别


# 调用前检查：当前 LLM 是否再次发起了相同的工具调用？总调用次数是否已经超限？
# 调用后检查：工具返回了什么结果？是否新增了证据？是否推进了某个调查阶段？
# 约定了sub-agent要给父agent的交付内容
class APIUsageOutput(TypedDict):
    api_usage_report: dict


logger = logging.getLogger(__name__)

def observe_node(node_name: str):
    def decorator(func):
        if inspect.iscoroutinefunction(func):
            @wraps(func)
            async def async_wrapper(state, *args, **kwargs):
                start = time.perf_counter()
                logger.info("node_started", 
                            # extra会把结构化字段附加到LogRecord上
                            extra={"node_name": node_name,
                                "state_keys": list(state.keys()),  # 只记录state的key列表，而不是全量内容
                                },
                )

                try:
                    result = await func(state, *args, **kwargs)

                    logger.info("node_finished",
                                extra={
                                    "node_name": node_name,
                                    "output_keys": list(result.keys()),
                                    "duration_ms": round((time.perf_counter() - start) * 1000,2),
                                    },
                                )
                    return result

                except Exception:
                    logger.exception("node_failed",
                                    extra={"node_name": node_name},)
                    raise   # 刚捕获到的异常原封不懂跑出去，让上一层感知到
            return async_wrapper
        else:
            @wraps(func)
            def sync_wrapper(state, *args, **kwargs):
                start = time.perf_counter()
                logger.info("node_started", extra={"node_name": node_name, "state_keys": list(state.keys())})
                try:
                    result = func(state, *args, **kwargs)
                    logger.info("node_finished", extra={
                        "node_name": node_name,
                        "output_keys": list(result.keys()) if isinstance(result, dict) else None,
                        "duration_ms": round((time.perf_counter() - start) * 1000, 2),
                    })
                    return result
                except Exception:
                    logger.exception("node_failed", extra={"node_name": node_name})
                    raise
            return sync_wrapper

    return decorator