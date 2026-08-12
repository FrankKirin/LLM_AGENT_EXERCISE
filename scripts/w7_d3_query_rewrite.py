"""
测试思路：
1.验证查询重写功能：能否把口语化的问题改为精准检索词
2.验证结果评估功能：能否正确判断检查结果质量
3.验证完整Agentic RAG流程：重写->检索->评估->(重写)->答案
4.验证最大检索次数限制：达到上限后强制生成答案
5.验证会话持久化：多伦对话状态是否保留
"""
import json
import asyncio
from langchain_core.messages import HumanMessage
from core.agentic_rag import build_agentic_rag_graph
from core.logger import logger

async def test_query_rewrite():
    """测试查询重写功能"""
    graph = build_agentic_rag_graph()
    config = {"configurable": {"thread_id": "rewrite_test_001"}}

    task = "那个什么AI Agent框架，就是LangChain出的那个图的形状的、叫啥来着？怎么用？"

    result = await graph.ainvoke(
        {
            "messages": [HumanMessage(content=task)],
            "original_query": task,
            "current_query": "",
            "retrieval_count": 0,
            "max_retrieval": 3,
            "is_satisfied": False,
            "final_answer": ""
        }, 
        config=config
    )

    logger.info(f"原始问题：{task}")
    logger.info(f"重写后查询：{result['current_query']}")
    logger.info(f"重写次数：{result['retrieval_count']}")
    logger.info(f"答案预览：{result['final_answer'][:150]}")

async def test_max_retrievals_limit():
    graph = build_agentic_rag_graph()

    config = {"configurable":{"thread_id":"limit_test_001"}}

    # 用一个很难的问题，设置max_retrievals=2
    task = "深度分析AI Agent未来10年的技术演进路径和商业应用格局"

    result = await graph.ainvoke(
        {
            "messages": [HumanMessage(content=task)],
            "original_query": task,
            "current_query": "",
            "retrieval_count": 0,
            "max_retrieval": 2,
            "is_satisfied": False,
            "final_answer": ""
        },
        config=config
    )

    logger.info(f"最大检索次数设置:2")
    logger.info(f"实际检索次数:{result['retrieval_count']}")
    assert result["retrieval_count"]<=2, "检索次数不应超过上限"
    logger.info(f"最终答案长度：{len(result['final_answer'])}")

async def test_full_flow():
    """
        全流程验证通过依据：
            1.最终答案不为空
            2.检索次数至少一次
    """
    config = {"configurable": {"thread_id":"test_full_001"}}
    graph = build_agentic_rag_graph()
    task = "介绍一下LangGraph的核心概念和基本用法"

    result = await graph.ainvoke(
        {
            "messages": [HumanMessage(content=task)],
            "original_query": task,
            "current_query": "",
            "retrieval_count": 0,
            "max_retrieval": 3,
            "is_satisfied": False,
            "final_answer": ""
        },
        config=config
    )
    assert result["final_answer"], "最终答案不应为空"
    assert result["retrieval_count"]>=1, "至少检索1次"
    logger.info("✅完整流程测试通过")


if __name__ == "__main__":
    # asyncio.run(test_query_rewrite())
    # asyncio.run(test_max_retrievals_limit())
    asyncio.run(test_full_flow())