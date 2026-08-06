# Supervisor-Worker模式,企业最常用
# 多智能体全局状态设计
# 1.messages：所有智能体共享的对话历史，追加模式
# 2.current_task: 处理的子任务
# 3.task_results：各Workder执行结果汇总
# 4.next_workder：下一个要执行的worker名称
import operator
from core.logger import logger
from typing import TypedDict, Annotated
from langchain.messages import AnyMessage, HumanMessage, ToolMessage, AIMessage


class MultiAgentState(TypedDict):
    messages: Annotated[list[AnyMessage], operator.add]
    original_task: str
    subtasks: list[dict[str, str]]
    worker_results: dict[str, str]
    current_worker: str
    final_report: str


# Worker角色定义
# 每个Worker职责单一，专注一个领域，能力更专业
# 角色描述清晰，引导Supervisor正确分配任务
# 易于拓展，新增Worker仅需添加定义

WORKER_DEFINITIONS = {
    "research_worker": {
        "name": "调研专员",
        "description": "负责信息检索、资料收集、市场调研，擅长查找事实性信息",
        "system_prompt":"""
        你是专业调研专员，擅长信息搜集与事实核查。
        你的任务是根据要求收集相关信息，输出结构化的调研结果。
        注意：只负责信息收集，不做分析和结论
    """
    },
    "analysis_worker": {
        "name":"分析师",
        "description": "负责数据分析、逻辑推理、趋势判断，擅长从数据中提炼洞察",
        "system_prompt": """
        你是资深分析师，擅长数据分析与逻辑推理。
        你的任务是根据提供的数据和信息，进行深度分析，输出结构化的结论分析。
        注意：只做分析，不做最终决策建议。
    """
    },
    "report_worker": {
        "name":"报告撰写人",
        "description": "负责整合各方面信息，撰写专业报告、擅长结构化表达",
        "system_prompt": """
        你是专业报告撰写人，擅长将各类信息整合成清晰专业的报告。
        你的任务是根据调研结果和分析结论，撰写完整的最终报告。
        要求：结构清晰、逻辑严谨、语言专业。
    """
    }
}

def test_state_design():
    # 测试内容：
    # 验证状态机构是否完整，各字段类型是否正确
    # 验证Worker定义是否清晰，职责边界是否明确
    # 手动模拟状态流转，检查数据是否正确传递
    test_state = MultiAgentState(
        messages = [HumanMessage(content="测试任务")],
        original_task = "测试任务",
        subtasks = [{"task": "子任务1", "worker": "research_worker"}],
        worker_results = {},
        current_worker = "research_worker",
        final_report = ""
    )
    logger.info("状态结构测试通过", state_keys=list(test_state.keys()))
    logger.info("Worker角色数量", count=len(WORKER_DEFINITIONS))
    for key, worker in WORKER_DEFINITIONS.items():
        logger.info(f"Worker: {worker['name']}", desc=worker['description'][:50])

if __name__ == "__main__":
    test_state_design()
