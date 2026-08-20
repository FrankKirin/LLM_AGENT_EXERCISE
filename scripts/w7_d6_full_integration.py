"""
用户提问
    ↓
记忆检索 - 从三级记忆中提取相关上下文
    ↓
查询重写 - 结合记忆上下文，优化检索词
    ↓
智能体检索 - 多策略检索 + 迭代优化
    ↓
答案生成 - 结合检索结果 + 记忆上下文生成答案
    ↓
记忆更新 - 对话结束后，提取新记忆存入长期记忆

核心价值：
个性化：智能体了解用户的背景、偏好、目标
上下文连贯：跨会话也能记住之前说过的
越用越懂你：用的越多，记忆越丰富，回答越精准
"""
import asyncio
from langchain_core.messages import HumanMessage, AIMessage
from core.logger import logger
from core.memory_manager import memory_manager
from core.agentic_rag import build_agentic_rag_graph

async def full_agentic_rag_with_memory(user_id: str, session_id: str, user_query: str)-> str:
    """
    带记忆的Agentic RAG完整流程
    这是对外的接口
    输入：
        user_id, session_id, 用户问题
    处理：
        根据query检索相关记忆，将记忆和用户query拼接成新的query，放入Agentic RAG中运行拿到result
        agentic_rag的结果作为AI message的短期记忆；query作为human message加入到短期记忆
    输出：
        Agentic RAG最终返回的结果
    """
    # logger.info(f"用户提问：{user_query}")

    # 检索相关记忆
    logger.info("Step1: 检索相关记忆...")
    memory_context = memory_manager.build_memory_context(user_query)
    logger.info(f"记忆上下文长度: {len(memory_context)}")
    # 构建带记忆的问题
    enhanced_query = f"""
    [用户记忆背景]
    {memory_context}

    [用户当前问题]
    {user_query}
    请结合用户背景和问题，进行检索和回答
    """
    # 执行Agentic RAG

    graph = build_agentic_rag_graph()
    config = {"configurable": {"thread_id": f"{user_id}_{session_id}"}}

    result = await graph.ainvoke({
        "messages": [HumanMessage(content=enhanced_query)],
        "original_query": user_query,
        "current_query": "",
        "retrieval_count": 0,
        "max_retrievals": 3,
        "is_satisfied": False,
        "final_answer": ""
    }, config = config)

    answer = result["final_answer"]

    # 更新短期记忆
    memory_manager.add_to_short_term(session_id, HumanMessage(content=user_query))
    memory_manager.add_to_short_term(session_id, AIMessage(content=answer))

    return answer

async def test_integration_basic():
    user_id = "integration_test_user"
    session_id = "session_001"

    from langchain_core.documents import Document
    test_memories = [
        Document(
            page_content="用户是B端产品经理，有4年经验",
            metadata={"type": "long_term_memory", "memory_type": "fact", "importance": "high", "user_id": user_id}
        ),
        Document(
            page_content="用户偏好实战学习，不喜欢太理论的内容",
            metadata={"type": "long_term_memory", "memory_type": "preference", "importance": "high", "user_id": user_id}
        ),
        Document(
            page_content="用户正在转型AI Agent工程师",
            metadata={"type": "long_term_memory", "memory_type": "goal", "importance": "high", "user_id": user_id}
        ),
    ]

    memory_manager.long_term.add_documents(test_memories)
    logger.info("已添加测试记忆：3条")

    query = "我应该怎么学习LangGraph?"
    answer = await full_agentic_rag_with_memory(user_id, session_id, query)

    logger.info(f"\n问题: {query}")
    logger.info(f"答案预览: {answer[:300]}...")

    history = memory_manager.get_short_term(session_id)
    assert len(history.messages) == 2, "应该有2条消息(用户+助手)"
    logger.info("✅ 基础整合流程测试通过")

async def test_multi_turn():
    user_id = "multi_turn_user"
    session_id = "session_002"

    # 第一轮
    answer1 = await full_agentic_rag_with_memory(
        user_id, session_id,
        "介绍一下AI Agent的基本概念"
    )
    logger.info(f"答案长度: {len(answer1)}")

    # 第二轮
    answer2 = await full_agentic_rag_with_memory(
        user_id, session_id,
        "那LangGraph又是什么?"
    )
    logger.info(f"答案长度: {len(answer2)}")

    history = memory_manager.get_short_term(session_id)
    logger.info(f"\n短期记忆消息数：{len(history.messages)}")
    assert len(history.messages) == 4, "应该有4条消息(2轮对话)"
    logger.info("✅ 多轮对话累积测试通过")


if __name__ == "__main__":
    asyncio.run(test_integration_basic())
