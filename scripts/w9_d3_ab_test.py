import random
from core.eval.ab_test import ab_manager
from core.logger import logger

def mock_run_version(is_new: bool) -> tuple[bool, float, float]:
    """
    输出：
        [success, latency, cost]
    """
    if is_new:
        # 新版本：成功率高、延迟低
        return random.random() > 0.1, random.uniform(0.8, 1.5), 0.002
    else:
        # 旧版本：成功率低，延迟高点
        return random.random() > 0.15, random.uniform(1.2, 2.2), 0.0025

def test_ab_flow():
    for i in range(200):
        sid = f"test_sid_{i}"
        group = ab_manager.get_group(sid, 0.5)
        success, latency, cost = mock_run_version(group == "B")
        ab_manager.record(group, success, latency, cost)

    report  = ab_manager.gen_report()
    for k,v in report.items():
        logger.info(f"{k}: {v}")
    logger.info("===== A/B测试统计完成 ====")

if __name__ == "__main__":
    test_ab_flow()

# 现实生产级流程
# 闭环流程（行业标准生产闭环）
# 线上真实流量 → 失败样本采集 → LLM归因分析 → 扩充离线测试集 → 版本优化 → 离线回归验证 → A/B灰度对照 → 全量发布 → 线上观测