"""
验证四种检索工具是否都能够正常调用
验证检索结果格式是否统一
验证智能体是否能够自主选择检索工具
验证多伦检索迭代是否正常工作
验证最大检索次数限制是否生效
"""
from core.logger import logger
from core.lc_baseline import llm
from core.agentic_rag import retrieval_tools, AGENTIC_RAG_PROMPT
from langchain.messages import SystemMessage, HumanMessage

async def test_agent_tool_selection():
    llm_with_tools = llm.bind_tools(retrieval_tools)

    # 测试用例: 不同类型问题应该选择不同工具
    test_cases = [
        ("什么是AI Agent的基本概念？", "概念性问题，应该选semantic_search"),
        ("LangGraph中StateGraph的具体用法", "精确API问题，应该选keyword_search"),
        ("对比LangGraph和AutoGen的优缺点", "对比分析问题，应该选hybrid_search"),
        ("AI Agent有哪些应用场景？", "调研类问题，应该选mmr_search"),
    ]

    for query, expected in test_cases:
        messages = [
            SystemMessage(content=AGENTIC_RAG_PROMPT),
            HumanMessage(content=query)
        ]

        response = await llm_with_tools.ainvoke(messages)

        logger.info(f"\n问题：{query}")
        logger.info(f"预期：{expected}")

        if response.tool_calls:
            for tc in response.tool_calls:
                logger.info(f"实际选择:{tc['name']}")
        else:
            logger.info("实际选择：未选择工具，直接回答")

    logger.info("\n✅ 工具选择测试完成（请观察智能体选择是否合理）")

if __name__ == "__main__":
    import asyncio
    import json
    asyncio.run(test_agent_tool_selection())