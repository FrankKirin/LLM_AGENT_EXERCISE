"""
流量哈希分流、指标统计、显著性检验、版本对比
"""
import hashlib
import statistics
from dataclasses import dataclass
from scipy import stats
from core.structured_logger import log_info

@dataclass
class ABMetric:
    sample_count: int = 0
    success_rate: float = 0.0
    avg_latency: float = 0.0
    avg_cost: float = 0.0

class ABTestManager():
    def __init__(self):
        self.group_data: dict[str, ABMetric] = {
            "A": ABMetric(),
            "B": ABMetric()
        }
        self.latency_records: dict[str, list[float]] = {"A":[], "B":[]}

    def get_group(self, session_id: str, traffic_radio: float=0.5):
        hash_val = int(hashlib.sha256(session_id.encode()).hexdigest(), 16) % 100
        return "B" if hash_val < traffic_radio*100 else "A"  # 不能是<=，0-49, 50-99

    def record(self, group:str, success:bool, latency: float, cost: float):
        """
            每来一个请求，就把请求的结果更新到对应分组的”样本数、成功率、平均延迟、平均成本“
        """
        g = self.group_data[group]
        g.sample_count += 1
        if success:
            g.success_rate = (g.success_rate * (g.sample_count-1) + 1) / g.sample_count
        else:
            g.success_rate = (g.success_rate * (g.sample_count-1)) / g.sample_count
        g.avg_latency = (g.avg_latency * (g.sample_count - 1) + latency) / g.sample_count
        g.avg_cost = (g.avg_cost * (g.sample_count - 1) + cost) / g.sample_count
        self.latency_records[group].append(latency)

    def stat_significance(self) -> tuple[bool, float]:
        # 根据至少10个样本评估T检验, 为gen_report做服务
        a_list = self.latency_records["A"]
        b_list = self.latency_records["B"]
        if len(a_list) < 10 or len(b_list) < 10:
            return False, 1.0  # 为什么是1.0
        _, p_value = stats.ttest_ind(a_list, b_list)
        return p_value < 0.05, p_value

    def gen_report(self) -> dict:
        sig, p_val = self.stat_significance()
        a = self.group_data["A"]
        b = self.group_data["B"]
        return {
            "A_group": {
                "sample": a.sample_count,
                "success_rate": round(a.success_rate, 4),
                "avg_latency": round(a.avg_latency, 3),
                "avg_cost": round(a.avg_cost, 6)
            },
            "B_group": {
                "sample": b.sample_count,
                "success_rate": round(b.success_rate, 4),
                "avg_latency": round(b.avg_latency, 3),
                "avg_cost": round(b.avg_cost, 6)
            },
            "significant": sig,
            "p_value": round(p_val, 4),
            "conclusion": self._get_conclusion(sig, a, b)
       }

    def _get_conclusion(self, sig: bool, a:ABMetric, b:ABMetric)->str:
        if not sig:
            return "样本不足或无统计学显著差异，建议继续放量观测"
        if b.success_rate > a.success_rate and b.avg_latency < a.avg_latency:
            return "新版本显著优于旧版本，可灰度转正"
        return "新版本性能退化，禁止全量发布"

ab_manager = ABTestManager()