from core.eval.offline_evaluator import evaluator
from core.logger import logger

def moick_agent_run(query: str)-> str:
    if "幻觉" in query:
        return "编造的虚假答案"
    return f"正常回答: {query}"

def test_offiline_regression():
    logger.info("====离线回归测试====")
    full_result = evaluator.full_regression_eval(moick_agent_run)
    for case_name, summary in full_result.items():
        logger.info(f"[{case_name}]")
        logger.info(f"用例总数:{summary.total_case}")
        logger.info(f"通过率:{summary.avg_success_rate:.2%}")
        logger.info(f"P95延迟:{summary.avg_latency_p95:.2f}")
        logger.info(f"超时率:{summary.timeout_rate:.2%}")
    logger.info("====离线回归测试完成====")

if __name__ == "__main__":
    test_offiline_regression()

