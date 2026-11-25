# 负责问题理解、Slot、上下文、追问判断
# 这个文件负责五件事情：
# 1. 定义 Slot Schema。
# 2. 让 LLM 识别 Intent 和提取 Slot。
# 3. 继承上一轮对话的 Slot。
# 4. 判断当前问题是否缺少必要 Slot。
# 5. 将 Slot 转换成 Chroma Metadata Filter。
from __future__ import annotations
import json
from pydantic import BaseModel, Field, ValidationError
from typing import Any
from typing import Literal

# 定义用户问题的Slot Schema
Intent = Literal[
    "general_qa",  # 通用qa
    "product_specific_qa",  # 产品说明
    "troubleshooting",  # 问题答疑
    "warranty_qa",  # 保修相关
]

class QuerySlots(BaseModel):
    # 产品品牌、产品型号、产品组件、故障类型、症状
    # slot根据实际业务要求自己定义
    product_brand: str|None = None
    product_model: str|None = None
    product_component: str|None = None
    issue_type: str|None = None
    symptom: str|None = None

class QueryAnalysis(BaseModel):
    """Query的分析结果
       LLM单次输出结构：意图、是否追问、槽位，改写后的查询
    """
    intent: Intent
    is_follow_up: bool = False
    # =QuerySlots()那么类定义加载时执行一次，所有实例可能会共享一个可变对象
    slots: QuerySlots = Field(default_factory=QuerySlots)
    rewritten_query: str  # 查询重写的目的就是为了能让重写后的query更贴合检索器

# 2.定义多轮对话需要保留的上下文
class QueryContext(BaseModel):
    # 已确认的Slot
    slots: QuerySlots = Field(default_factory=QuerySlots)
    last_intent: Intent|None = None
    last_query: str|None = None

    # 如果上一轮正在等待用户补充信息，保留待完成的问题
    pending_query: str|None = None
    pending_intent: Intent|None = None
    pending_slots: QuerySlots = Field(default_factory=QuerySlots)

# 3.定义每种Intent对应必要的Slot
# 澄清机制，基于意图的必要槽位校验
INTENT_REQUIRED_SLOTS = {
    "general_qa":[],
    "product_specific_qa":["product_model"],
    "troubleshooting": [],
    "warranty_qa": ["product_model"],
}

# 如果slot缺少的是产品，给出的反问句
SLOT_QUESTIONS = {
    "product_model": "请问你的冰箱具体型号是什么？可以在冰箱内部的产品铭牌上找到。",
}

# 普通追问时，优先继承相对稳定的产品身份信息
# 不自动继承上一轮的故障症状，避免把旧问题代入新问题
IDENTITY_SLOT_FIELDS = (
    "product_brand",
    "product_model",
)

# 对正在等待补充信息的问题，保留该问题已有的全部Slot
ALL_SLOT_FIELDS = tuple(QuerySlots.model_fields.keys())

# ============================================================
# 4. 定义 Slot 与 Chroma Metadata 的映射
# ============================================================

METADATA_FILTER_FIELD_MAP = {
    "product_brand": "product_brand",
    "product_model": "product_model",
}

def merge_slots(
    current_slots: QuerySlots,
    previous_slots: QuerySlots,
    inherit_fields: tuple[str, ...],
) -> QuerySlots:
    """合并本轮Slot和上轮Slot, 本轮明确提供的值优先。"""
    current_data = current_slots.model_dump()
    previous_data = previous_slots.model_dump()

    for field_name in inherit_fields:
        if current_data[field_name] is None:
            current_data[field_name] = previous_data

    return QuerySlots.model_validate(current_data)

def get_missing_required_slots(
    intent: Intent,
    slots: QuerySlots,
) -> list[str]:
    """根据当前Intent，计算缺失的必要Slot。"""
    required_slots = INTENT_REQUIRED_SLOTS.get(intent)

    if required_slots is None:
        raise ValueError(f"未知的intent：{intent}")

    missing_slots = [
        slot_name for slot_name in required_slots if getattr(slots, slot_name) is None
    ]

    return missing_slots

def build_metadata_filter(
    slots: QuerySlots,
    enable_metadata_fields: set[str],
) -> dict[str, Any] | None:
    """
    只使用已经确认存在于知识库中的Metadata字段构造过滤条件
        输入:
            enable_metadata_fields: 知识库中真实存在的元数据字段集合
        处理：
            单条件直接返回、多条件自动包装成$and,符合Chroma的filter语法
        输出：
    """
    # 把已经提取到的槽位，转换成向量数据库Chroma能立即的的metadata过滤条件，缩小检索范围
    slot_data = slots.model_dump()
    conditions = []

    for slot_name, metadata_field in METADATA_FILTER_FIELD_MAP.items():

        if metadata_field not in enable_metadata_fields:
            continue

        slot_value = slot_data[slot_name]

        if slot_value is None:
            continue

    if not conditions:  # 一个条件都没有，不过滤，纯语义检索
        return None

    if len(conditions) == 1:  # 只有一个条件，直接返回
        return conditions[0]

    # 多个条件，$and操作符，两个标签都要匹配
    return {
        "$and": conditions
    }

# ============================================================
# 5. Query Understanding 主服务
# ============================================================

class QueryUnderstandingService:
    def __init__(
        self,
        llm: Any,
        enabled_metadata_fields: set[str] | None = None,
    ):
        self.llm = llm
        # 只允许过滤已经真实存在的Metadata字段
        self.enabled_metadata_fields = (
            enabled_metadata_fields or set()
        )

    def _extract_with_llm(
        self,
        user_query: str,
        context: QueryContext,
    ) -> QueryAnalysis:
        """调用LLM识别Intent、提取Slot并改写Query。"""

        context_data = {
            "last_query": context.last_query,
            "last_intent": context.last_intent,
            # 当前活跃的槽位状态
            "active_slots": context.slots.model_dump(),
            # 待补全问题的“挂起状态”
            "pending_query": context.pending_query,  # 上一轮缺少必要槽位发起追问的原始问题
            "pending_intent": context.pending_intent,  # 挂起问题的原始意图
            "pending_slots": context.pending_slots.model_dump(),  # 挂起问题已有的槽位
        }

        prompt = f"""
    你是一个家电企业知识库的 Query Understanding 模块。

    你的任务：
    1. 判断用户问题的 Intent。
    2. 提取用户问题中的 Slot。
    3. 判断是否为多轮对话的延续。
    4. 将用户问题改写为适合独立检索的完整 Query。

    Intent 只能是以下四种之一：
    - general_qa：普通知识问答
    - product_specific_qa：需要特定产品型号才能准确回答的问题
    - troubleshooting：故障排查
    - warranty_qa：保修政策问题

    Slot Schema：
    {{
        "product_brand": null,
        "product_model": null,
        "product_component": null,
        "issue_type": null,
        "symptom": null
    }}

    上下文信息：
    {json.dumps(context_data, ensure_ascii=False)}

    当前用户输入：
    {user_query}

    提取规则：
    1. 不确定的信息必须填写 null，不能猜测型号或故障。
    2. 用户明确提供的新信息优先于历史信息。
    3. 如果 pending_query 不为空，说明系统上一轮正在等待用户补充信息。
    此时应当把当前输入理解为对原始问题的补充，保留原始问题的 Intent 和已有 Slot。
    4. 如果用户是在延续上一轮问题，应设置 is_follow_up=true。
    5. 如果用户切换到全新的问题，应设置 is_follow_up=false。
    6. rewritten_query 必须是一个完整、明确、可以独立检索的问题。
    7. 如果用户在回答追问，rewritten_query 应当整合原始问题与当前补充信息。
    8. 不得添加用户没有提供、上下文也无法确定的信息。

    严格只返回 JSON，不要输出 Markdown，不要解释。

    返回格式：
    {{
        "intent": "general_qa",
        "is_follow_up": false,
        "slots": {{
            "product_brand": null,
            "product_model": null,
            "product_component": null,
            "issue_type": null,
            "symptom": null
        }},
        "rewritten_query": "完整的检索问题"
    }}
    """
        response = self.llm.invoke(prompt)
        content = response.content

        if not isinstance(content, str):
            raise TypeError("LLM返回的content不是字符串")

        # 允许模型偶尔返回MarkDown代码围栏
        start = content.find("{")
        end = content.rfind("}")

        if start<0 or end < start:
            raise ValueError("LLM没有返回有效的JSON对象")

        json_content = content[start: end+1]

        try:
            data = json.loads(json_content)
            return QueryAnalysis.model_validate(data)
        except (json.JSONDecodeError, ValidationError) as exc:
            # JSONDecodeError解决文本不是合法JSON，解析阶段失败
            # ValidationError解决JSON合法，但是Schema不合法的情况
            raise ValueError(
                "Query Understanding返回的数据不符合Schema约定"
            ) from exc

    def run(self, user_query:str, context: QueryContext) -> QueryUnderstandingResult:
        """完成问题理解、上下文合并、必要Slot判断和Filter构造
           处理：提取5个预设的slot; 判断intent； 改写可独立检索的query
        """
        # 1.提取Intent和当前问题的Slot
        analysis = self._extract_with_llm(
            user_query=user_query,
            context=context,
        )

        # 2.决定是否继承历史Slot
        # - 用户正在回答上一轮追问
        # - 普通多轮对话，只继承稳定的产品身份信息
        # - 全新问题，不继承上一轮Slot
        pending_reply = context.pending_query is not None
        if pending_reply:  # 回答追问, 系统主动追问
            intent = context.pending_intent or analysis.intent
            resolved_slots = merge_slots(
                current_slots=analysis.slots,
                previous_slots=context.pending_slots,
                inherit_fields=ALL_SLOT_FIELDS,
            )
        elif analysis.is_follow_up:  # 上一轮追问(普通追问), 用户自己追问
            intent = analysis.intent
            resolved_slots = merge_slots(
                current_slots=analysis.slots,
                previous_slots=context.slots,
                inherit_fields=IDENTITY_SLOT_FIELDS,
            )
        else: # is_follow_up=False的场景
            intent = analysis.intent
            resolved_slots = analysis.slots

        # 3.根据Intent规则检查必要Slot
        required_slots = INTENT_REQUIRED_SLOTS[intent]
        missing_slots = get_missing_required_slots(
            intent=intent,
            slots=resolved_slots,
        )
        # 如果还存在missing slots，那么设置澄清标志为True
        needs_clarification = len(missing_slots)>0
        clarification_question = None

        if needs_clarification:
            # 单字段追问策略，一次只问一个最关键的缺失字段
            # 追问状态持久化：如果补全后仍有确实，pending_query会继续保留原始问题，形成”渐进式补全“
             clarification_question = SLOT_QUESTIONS[missing_slots[0]]

        # 4.构造Chroma Filter
        metadata_filter = build_metadata_filter(
            slots=required_slots,
            enable_metadata_fields=self.enabled_metadata_fields,
        )

        # 5.保存下一轮需要的对话上下文
        if needs_clarification:
            pending_query = (
                context.pending_query if pending_reply else user_query
            )
            next_context = QueryContext(
                slots=resolved_slots,
                last_intent=intent,
                last_query=user_query,
                pending_query=pending_query,
                pending_intent=intent,
                pending_slots=resolved_slots,
            )
        else:
            # 已经具备必要信息，清除追问状态
            next_context = QueryContext(
                slots=resolved_slots,
                last_intent=intent,
                last_query=user_query,
            )
        return QueryUnderstandingResult(
            intent=intent,
            slots=resolved_slots,
            rewritten_query=analysis.rewritten_query,
            required_slots=required_slots,
            missing_slots=missing_slots,
            needs_clarification=needs_clarification,
            clarification_question=clarification_question,
            metadata_filter=metadata_filter,
            next_context=next_context,
        )

# ============================================================
# 6. Query Understanding 的统一返回结构
# ============================================================

class QueryUnderstandingResult(BaseModel):
    intent: Intent  # 意图
    slots: QuerySlots  # 槽位
    rewritten_query: str  # 重写后，适合检索的query

    required_slots: list[str] = Field(default_factory=list) # 必须的槽位
    missing_slots: list[str] = Field(default_factory=list)  # 缺失的槽位

    needs_clarification: bool = False
    clarification_question: str|None = None

    metadata_filter: dict[str, Any] | None = None
    next_context: QueryContext  # 作用是什么？为什么要有这个变量
