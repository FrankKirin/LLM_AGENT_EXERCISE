import asyncio
from core.logger import logger
from langchain_core.messages import HumanMessage
from core.memory_agent import build_memory_agent_graph
from core.memory_agent import MemoryAgentState


async def test_memory_extraction():
    """验证能否正确判断是否有新信息 
    """
    conversation = """
    用户：你好，我叫王小明
    助手：你好王小明！很高兴认识你。
    用户：我是一名后端开发工程师，工作3年了
    助手：后端开发背景很不错啊。
    用户：我现在想转型做AI Agent开发
    助手：这是个很好的方向，很有前景。
    用户：我比较喜欢实战学习，不太喜欢太理论的内容
    助手：好的，我会多给你实战项目。
    用户：我住在杭州，平时喜欢打羽毛球
    助手：羽毛球是很好的运动！
    """
    graph = build_memory_agent_graph()

    config = {"configurable":{"thread_id": "mem_test_001"}}

    result = await graph.ainvoke(
        {
            "messages": [HumanMessage(content="分析这段对话")],
            "conversation_text": conversation,
            "extracted_memories": [],
            "existing_memories": [],
            "final_memories": [],
            "user_id": "test_user_wang"
        },
        config=config
    )

    assert len(result["extracted_memories"])>0, "不足够提取到记忆"
    logger.info("记忆提取测试通过")

async def test_no_new_info():
    graph = build_memory_agent_graph()
    config = {"configurable": {"thread_id": "mem_test_002"}}

    # 普通闲聊，没有新信息
    conversation = """
    用户：今天天气真好啊
    助手：是啊，很适合出门。
    用户：中午吃什么好呢？
    助手：看你口味啦，想吃什么？
    """
    result = await graph.ainvoke(
        {
            "messages": [HumanMessage(content="分析这段对话")],
            "conversation_text": conversation,
            "extracted_memories": [],
            "existing_memories": [],
            "final_memories": [],
            "user_id": "test_user_wang"
        },
        config=config
    )

    logger.info(f"提取到的记忆数量{len(result['extracted_memories'])}")

if __name__ == "__main__":
    # asyncio.run(test_memory_extraction())
    asyncio.run(test_no_new_info())