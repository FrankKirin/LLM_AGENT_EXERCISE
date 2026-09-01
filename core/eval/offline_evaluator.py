"""
Week9 Day1 离线回归评估引擎
特性：
1. 三类测试集：标杆用例、长尾用例、对抗用例
2. 批量自动化评测
3. 版本对比、自动识别退化
4. 适配所有LangGraph Agent
"""
import json
import os
from core.structured_logger import log_info, log_warning
from core.eval.eval_metrics import AgentEvalMetric, AgentEvalSummary, MetricCalculator
import time
from typing import Callable, Any

CASE_PATH = "datasets"

class OfflineEvaluator:
    def __init__(self):
        self.case_types = ["hero_case", "long_tail_case", "adversarial_case"]
        self.cases: dict[str, list[dict]] = self._load_all_cases()

    def _load_all_cases(self) -> dict[str, list[dict]]:
        all_cases = {}
        for case_type in self.case_types:
            file_path = os.path.join(CASE_PATH, f"{case_type}.json")
            if os.path.exists(file_path):
                with open(file_path, "r", encoding="utf-8") as f:
                    all_cases[case_type] = json.load(f)
            else:
                all_cases[case_type] = []
        return all_cases

    def run_single_eval(self, query:str, expect: dict[str, Any], run_func: Callable):
        """
        输入：
        处理：
        输出：
        """
        metric = AgentEvalMetric()
        try:
            start_time = time.time()
            resp = run_func(query)
            metric.full_latency = round(time.time() - start_time, 4)

            if expect.get("key_contain"):
                # 如果key要求包含哪些value，看一下是否包含，包含返回1，否则返回0
                metric.task_success = 1.0 if all(k in resp for k in expect["key_contain"]) else 0.0
            else:
                metric.task_success = 1.0

            metric.is_timeout = metric.full_latency > expect.get("timeout", 10)

        except Exception as e:
            log_warning("离线用例执行失败", query=query, error=str(e))
            metric.task_success=0.0
            metric.is_timeout = True
        return metric

    def batch_eval(self, case_type: str, run_func: Callable)->AgentEvalSummary:
        case_list = self.cases.get(case_type, [])
        metric_list = []
        for case in case_list:
            metric = self.run_single_eval(
                query = case["query"],
                expect=case.get("expect", {}),
                run_func=run_func
            )
            metric_list.append(metric)
        return MetricCalculator.build_summary(metric_list)

    def full_regression_eval(self, run_func: Callable) -> dict[str, AgentEvalSummary]:
        """全量回归测试：所有数据集跑一遍"""
        log_info("开始全量立项回归评估")
        result = {}
        for case_type in self.case_types:
            result[case_type] = self.batch_eval(case_type, run_func)
            log_info(f"{case_type} 评测完成，成功率:{result[case_type].avg_success_rate:2f}")
        return result

evaluator = OfflineEvaluator()
