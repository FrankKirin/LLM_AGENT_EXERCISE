import asyncio
from core.eval.llm_judge import judge
from core.logger import logger

async def test_llm_judge():
    logger.info("===== Week9 Day2 LLM-Judge 评测测试 =====")

    # 测试1：正常回答
    res1 = await judge.score(
        query="什么是LangGraph？",
        context="LangGraph是LangChain推出的用于构建多轮Agent的框架",
        response="LangGraph是LangChain官方的Agent流程编排框架"
    )
    logger.info("【正常回答打分】")
    if res1:  # 考虑到res1可能返回None的情况
        logger.info(f"幻觉分：{res1.hallucination_score}")
        logger.info(f"忠实度：{res1.faithfulness}")
        logger.info(f"有用性：{res1.usefulness}")
        logger.info(f"原因：{res1.reason}")

    res2 = await judge.score(
        query="什么是LangGraph？",
        context="LangGraph是LangChain推出的用于构建多轮Agent的框架",
        response="LangGraph是Google推出的深度学习框架"
    )
    logger.info("\n【幻觉回答打分】")
    if res2:
        logger.info(f"幻觉分：{res2.hallucination_score}")
        logger.info(f"忠实度：{res2.faithfulness}")
        logger.info(f"有用性：{res2.usefulness}")
        logger.info(f"原因：{res2.reason}")

    logger.info("===== LLM裁判评测完成 =====")

if __name__ == "__main__":
    asyncio.run(test_llm_judge())