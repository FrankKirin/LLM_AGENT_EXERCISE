"""
自动化采集线上失败案例、幻觉案例、超时案例、拒绝案例、自动归类故障类型，沉淀为测试集
"""
import json
import os
from dataclasses import dataclass, asdict
from core.structured_logger import log_info

FAILURE_SAVE_PATH = "datasets/online_failure.json"

@dataclass
class FailureCase:
    session_id: str
    query: str
    response: str
    error_type: str
    latency: float
    timestamp: float
    trace_id: str

class FailureCollector:
    def __init__(self):
        # 数据结构：[{FailureCase}]
        self.fail_record = self._load()

    def _load(self) -> list:
        # 从已有文件读取，没有就返回空
        if os.path.exists(FAILURE_SAVE_PATH):
            # 如果没有encoding参数，会使用操作系统默认编码,windows会用gbk，导致报错
            with open(FAILURE_SAVE_PATH, "r", encoding="utf-8") as file:
                data = json.load(file)
                return data
        return []

    def save(self):
        # 写入到指定文件
        with open(FAILURE_SAVE_PATH, "w", encoding="utf-8") as file:
            json.dump(self.fail_record, file, ensure_ascii=False, indent=2)

    def collect(self, session_id: str, query: str, response: str,
                error_type:str, latency: float, timestamp:float, trace_id: str):
        # 采集
        # 创建并保存到指定文件
        case = FailureCase(
            session_id=session_id,
            query=query,
            response=response,
            error_type=error_type,
            latency=latency,
            timestamp=timestamp,
            trace_id=trace_id,
        )
        self.fail_record.append(asdict(case))
        self.save()
        log_info("线上失败样本已采集", error_type=error_type, query=query[:30])

    def export_to_testset(self):
        # 线上失败样本转为离线回归测试用例
        # out_path = "datasets/online_export_case.json"
        # 每个case加入”query“, "expect", "source", "error_type"
        # 通过json.dump导出
        export = []
        for case in self.fail_record:
            export.append({
                "query":case["query"],
                "expect": {"timeout": 10},
                "source": "online_failure",
                "error_type": case["error_type"]
            })
        out_path = "datasets/online_export_case.json"
        with open(out_path, "w", encoding="utf-8") as f:
            # indent=2， 每深入一层JSON，就缩2个空格
            json.dump(export, f, ensure_ascii=False, indent=2)
        log_info(f"已导出{len(export)}条线上样本为回归用例")

collector = FailureCollector()