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

class CauseEvidence(BaseModel):  # 运行时的类
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

# 验证JSON语法是否有效；字段类型和值是否符合契约
def parse_report_json(raw_text: str)-> APIUsageReport:
    try:
        payload = json.loads(raw_text)  # str转到obj
        return APIUsageReport.model_validate(payload)
    except (json.JSONDecodeError, ValidationError) as exc:
        raise ValueError(f"API Usage报告无效: {exc}") from exc


class ParentState(TypedDict):   # 静态标注
    user_query: str
    start_date: str
    end_date: str

    # pending; completed; other
    api_status: str
    active_agent: str

    api_result: list[dict[str, Any]]    

    anomaly_detected: bool  # 是否检测到异常
    possible_causes: list[str] # 可能原因

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


# 数据分层：
# （1）子图内部State
# （2）子图的业务结果
# （3）父图State
#  (4) Context