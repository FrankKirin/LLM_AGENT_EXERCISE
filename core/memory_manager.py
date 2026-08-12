"""
短期记忆：InMemoryChatMessageHistory
中期记忆：对话摘要，节省token
长期记忆：向量存储，存重要事实和偏好
why？
- 短期记忆完整但贵
- 长期记忆便宜但不完整
- 分级使用，在成本和效果之前找平衡
"""
import json
from core.logger import logger
from core.config import settings
from langchain_core.messages import HumanMessage, AnyMessage, AIMessage
from langchain_core.chat_history import InMemoryChatMessageHistory
from core.lc_baseline import llm
from core.rag_vector_store import get_vector_store
from langchain_core.documents import Document
from langchain_chroma import Chroma

class MemoryManager:
    """
    三级记忆管理器
    """
    def __init__(self, user_id: str="default_user"):
        # 为什么这里要设置一个default_user？
        self.user_id = user_id

        # 短期记忆
        self.short_term: dict[str, InMemoryChatMessageHistory] = {}

        # 中期记忆
        # key=session_id, value=摘要文本
        self.medium_term: dict[str, str] = {}
        # 为什么中期记忆不用user_id来标识？

        # 长期记忆：向量存储(服用RAG的向量库)
        self.long_term :Chroma = get_vector_store()

        logger.info("三级记忆管理器初始化完成", user_id=user_id)

    # 短期记忆操作
    def get_short_term(self, session_id: str) -> InMemoryChatMessageHistory:
        """获取指定会话的短期记忆"""
        if session_id not in self.short_term:
            self.short_term[session_id] = InMemoryChatMessageHistory()
        # 巧妙包含已有和新建的情况
        return self.short_term[session_id]

    def add_to_short_term(self, session_id: str, message: AnyMessage):
        history = self.get_short_term(session_id)
        history.add_message(message)

    # 中期记忆：会话摘要
    # 设计思路：
    # 对话达到一定轮数，或者会话结束时
    # 短期记忆压缩成摘要，存入中期记忆
    # 会话开始时，可以快速回顾历史
    async def generate_session_summary(self, session_id: str)->str:
        """会话压缩成摘要，存入中期记忆
        1.拿到短期会话历史：太短->不存，够长->存入摘要 
        2.拿到会话历史并进行拼接，AI和Human的都拿
        3.写好prompt，让llm进行摘要
        4.摘要存入中期记忆
        """
        history = self.get_short_term(session_id)
        messages = history.messages
        if len(messages) < 2:
            logger.info("消息太少，无需摘要", session_id=session_id)
            return ""

        # human_message = "\n".join(
            # [str(x.content) for x in messages if x.type=="human"]
        # )
        all_messages = "\n".join([
            f"{'用户' if m.type=='human' else '助手'}:{m.content}"
            for m in messages
        ])

        logger.debug(f"all_messages内容：{all_messages}")

        prompt = f"""
            你是一个擅长总结对话内容的分析师

            要求：
            1.保留用户明确表达的需求、目标、偏好、约束条件和重要事实
            2.保留已经确定的结论、已经完成的操作、当前任务进展以及待解决的问题。
            3.保留对未来回答有帮助的上下文关系，避免只保留孤立事实
            4.删除寒暄、重复表达、无关闲聊和已经失去价值的临时信息
            5.不要添加对话中没有出现的信息，不要自行推测

            请对以下这段内容进行摘要，供未来AI Agent使用
            {all_messages}
        """
        response = await llm.ainvoke(input=prompt)
        summary = str(response.content)

        logger.debug(f"The result of session memory from llm: {summary}")

        self.medium_term[session_id] = summary

        return summary

    async def extract_long_term_memories(self, session_id: str) -> list[str]:
        """从会话中提取重要事实，存入长期记忆"""
        history = self.get_short_term(session_id)
        messages = history.messages

        if len(messages)<4:
            return []

        message_text = "\n".join([
            f"{'用户' if m.type=='human' else '助手'}: {m.content}"
            for m in messages
        ])

        prompt = f"""
        请从以下对话中提取值得长期记住的重要格式，格式为JSON数组：
        - 用户的个人信息（职业、背景、偏好等）
        - 用户明确表达的喜好、习惯、观点
        - 重要的事实和知识
        - 用户的目标和计划

        每条信息用一句话表述

        对话内容：
        {message_text}

        输出JSON数组格式：["记忆1", "记忆2", ...]
        """

        response = await llm.ainvoke(prompt)
        
        try:
            # 异常捕获：因为llm的输出不一定是完全可信的JSON数据
            memories = json.loads(response.content)
            # 如果是返回是个list，做成Chroma向量库形式
            if isinstance(memories, list):
                docs = [
                    Document(page_content=m, metadata={"session_id":session_id,"user_id": self.user_id, "type":"long_term_memory" })
                    for m in memories
                ]
                if docs:
                    self.long_term.add_documents(docs)
                    logger.info("长期记忆提取完成", count=len(docs))
                return memories # 把提取结果给调用方
        except json.JSONDecodeError as e:
            logger.error("长期记忆提取失败", error=str(e))

        return []

    # 记忆检索
    # 检索长期记忆(事实和偏好)，中期记忆(会话摘要)组合成上下文，注入到智能体
    def retrieve_relevant_memories(self, query: str, top_k: int=3) -> dict:
        # 返回一个字典{"long_term":[], "summary": []}
        # 对于long_term通过langchain封装的as_retriever
        # 然后用search_type, 参数k和filter针对long_term数据进行检索，filter用来过滤元数据
        # 中期记忆获取：摘取最近N个会话摘要
        result = {
            "long_term": [],
            "medium_term": []
        }
        retriever = self.long_term.as_retriever(
            search_type = "similarity",
            kwargs={"k":top_k, "filter": {"type": "long_term_memory"}}
        )
        try:
            pages = retriever.invoke(query)
            result["long_term"] = [x.page_content for x in pages]
        except Exception as e:
            logger.warning("长期记忆检索失败", error=str(e))

        recent_summaries = list(self.medium_term.values())[-3:]
        result["medium_term"] = recent_summaries

        return result

    def build_memory_context(self) -> str:
        # 构建上下文字符串，用于注入到prompt中
        # 输入是用户的query，根据用户的query，搜索最相关的的长期记忆和中期摘要
        """
        【关于用户的已知信息】
        1. 用户是一名AI产品经理
        2. 用户正在学习LangGraph

        【最近对话摘要】
        会话1：用户最近在学习Agent Memory...
        """
        memories = self.retrieve_relevant_memories(query)

        context_parts = []

        if memories["long_term"]:
            context_parts.append("【关于用户的已知信息】")
            for num, detail in enumerate(memories["long_term"], 1):
                context_parts.append(f"{num}.{detail}")
        if memories["medium_term"]:
            context_parts.append("【最近对话摘要】")
            for num, detail in enumerate(memories["medium_term"], 1):
                context_parts.append(f"会话{num}:{detail}")

        # 不返回“”,是因为这段文字很可能被塞进prompt中使用
        # if else语句很重要,不然没有记忆会返回None，和函数返回结果不一致
        return str("\n".join(context_parts)) if context_parts else "（暂无历史记忆）"

# 全局单例
memory_manager = MemoryManager()
    
if __name__ == "__main__":
    memery = MemoryManager()

    session_id = "frank_test_001"
    memery.add_to_short_term("frank_test_001", HumanMessage(content="2026年对初级AI Agent工程师的技能有什么要求？"))
    memery.add_to_short_term("frank_test_001", HumanMessage(content="有了LLM是不是不需要AI Agent工程师写代码了？"))
    memery.add_to_short_term("frank_test_001", HumanMessage(content="AI产品经理和AI Agent工程师薪资哪个高？"))

    import asyncio
    result = asyncio.run(memery.generate_session_summary(session_id))
