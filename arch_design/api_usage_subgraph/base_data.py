# from typing import TypedDict, Any, Annotated # python 3.12后大胆用这个
from typing_extensions import TypedDict, Any, Annotated, Literal # python多版本兼容用这个
from pydantic import BaseModel, Field
from langgraph.graph.message import add_messages
import json
from pydantic import ValidationError

class AppContext(TypedDict):
    tenant_id: str
    user_id: str | None
    session_id: str | None

class CauseEvidence(BaseModel):
    # need_verification作用是什么？
    cause: str
    evidence: list[str] = Field(default_factory=list)
    confidence: Literal["low", "medium", "high"] = "low"

    need_verification: bool = True

# Pydantic会验证字段的类型和声明的取值范围
class APIUsageReport(BaseModel):
    # 完成、数据不足，失败
    status: Literal["completed", "insufficient_data", "failed"]
    start_date: str
    end_date: str

    anomaly_detected: bool | None = None

    trend_summary: str = ""
    possible_causes: list[CauseEvidence] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
    error_code: str | None = None

def parse_report(raw_text: str):
    try:
        # Json能否解析，字段类型是否正确，必填字段是否存在
        payload = json.loads(raw_text) # str to obj
        # 即使结构正确，字段间关系是否符合规定的业务契约
        report = APIUsageReport.model_validate(payload)
    except (json.JSONDecodeError, ValidationError) as exc:
        raise ValueError(
            f"APIUsageReport格式校验失败: {exc}"
        ) from exc # 怎么理解这个from exc
    # 业务语义校验:
    # completed代表分析成功完成
    # 必须有明确的True / False检测结论
    # 如果校验失败，可以单独设置一个报告修复节点，最多修复一次[未实现]
    if report.status == "completed" and report.anomaly_detected is None:
        raise ValueError("status=completed时，anomaly_detected必须是布尔值")

    return report.model_dump(mode="json")


class ParentState(TypedDict):   # 静态标注
    user_query: str
    start_date: str
    end_date: str

    # pending; completed; other
    # api_status：路由函数看的控制流
    # active_agent：控制流字段
    api_status: str
    active_agent: str

    api_result: list[dict[str, Any]]    

    anomaly_detected: bool  # 是否检测到异常
    possible_causes: list[str] # 异常可能原因

    final_answer: str


class APIUsageState(TypedDict):

    # 自动累加的历史消息记录
    messages: Annotated[list, add_messages]
    user_query: str
    start_date: str
    end_date: str

    api_result: list[dict[str, Any]] # 作用是什么?
    anomaly_detected: bool

    # 中间结果
    history_result: str # 历史日志
    rag_result: str

    # 调查进度
    # history_checked: bool
    # rag_checked: bool
    # analysis_completed: bool

    # 子图分析过程
    possible_causes: list[str]

    # Loop Guard，循环监控
    tool_call_count: int # 已经尝试执行工具调用总数
    last_action_signature: str # 上一轮工具调用名称和参数
    # last_result_signature: str
    # no_progress_count: int

    same_action_count: int  # 连续生成相同工具调用的轮数
    loop_guard_triggered: bool  # 触发了保护
    stop_reason: str  # 停止的原因

# 调用前检查：当前 LLM 是否再次发起了相同的工具调用？总调用次数是否已经超限？
# 调用后检查：工具返回了什么结果？是否新增了证据？是否推进了某个调查阶段？


