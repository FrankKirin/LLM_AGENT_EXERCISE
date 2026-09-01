from dataclasses import dataclass, field
from typing import Dict, Any, List
import time


@dataclass
class AgentEvalMetric:
    # 质量指标
    task_success: float = 0.0
    hallucination_score: float = 0.0
    faithfulness: float = 0.0
    usefulness: float = 0.0

    # Agent功能指标
    tool_call_accuracy: float = 0.0
    iterate_step_valid: bool = False

    # 性能指标
    first_token_latency: float = 0.0
    full_latency: float = 0.0
    is_timeout: bool = False

    # 成本指标
    prompt_tokens: int = 0
    completion_tokens: int = 0

    # 安全指标
    injection_risk: bool = False
    privacy_leak: bool = False

@dataclass
class AgentEvalSummary:
    """批量评估汇总报告"""
    total_case: int = 0
    pass_case: int = 0
    avg_success_rate: float = 0.0
    avg_hallucination: float = 0.0
    avg_faithfulness: float = 0.0
    avg_latency_p95: float = 0.0
    total_prompt_tokens: int = 0
    total_completion_tokens: int = 0
    timeout_rate: float = 0.0
    injection_block_rate: float = 0.0
    # 每次创建实例调用list()新建一个空列表
    fail_cases: list[dict[str, Any]] = field(default_factory=list)

class MetricCalculator:
    @staticmethod
    def calc_success_rate(success_list: list[bool]) -> float:
        # [True, False, True]
        if not success_list:
            return 0.0
        return sum(success_list) / len(success_list)

    @staticmethod # 如果需要访问类变量的函数，则定义为classmethod
    def calc_p95_latency(latency_list: list[float]) -> float:
        if not latency_list:
            return 0.0
        sorted_lat = sorted(latency_list)
        idx = int(len(sorted_lat) * 0.95)
        return sorted_lat[idx]

    @staticmethod
    def build_summary(metric_list: list[AgentEvalMetric]) -> AgentEvalSummary:
        summary = AgentEvalSummary()
        summary.total_case = len(metric_list)
        if not metric_list:
            return summary

        success_list = [m.task_success >= 0.8 for m in metric_list]
        latency_list = [m.full_latency for m in metric_list if m.full_latency > 0]
        timeout_list = [m.is_timeout for m in metric_list]

        summary.pass_case = sum(success_list)
        summary.avg_success_rate = sum(success_list) / len(success_list)
        summary.avg_hallucination = sum([m.hallucination_score for m in metric_list]) / len(metric_list)
        summary.avg_faithfulness = sum([m.faithfulness for m in metric_list]) / len(metric_list)
        summary.avg_latency_p95 = MetricCalculator.calc_p95_latency(latency_list)
        summary.timeout_rate = sum(timeout_list) / len(timeout_list)

        summary.total_prompt_tokens = sum([m.prompt_tokens for m in metric_list])
        summary.total_completion_tokens = sum([m.completion_tokens for m in metric_list])

        return summary
