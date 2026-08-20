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

        # 长期记忆：向量存储(复用RAG的向量库)
        self.long_term :Chroma = get_vector_store()

        logger.info("三级记忆管理器初始化完成")

    # 短期记忆操作
    def get_short_term(self, session_id: str) -> InMemoryChatMessageHistory:
        """
            输入：
                session_id
            处理：
                查找对应session_id的短期记忆是否被创建，返回对应session_id的历史会话
            输出：
                InMemoryChatMessageHistory对象，通过.messages访问所有消息内容，数据结构: [AnyMessage] 
        """
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
        输入：
            用户session_id
        处理：
            用session_id拿到对应历史消息
            <2，判断无需摘要
            ≥2，构造一个列表[用户/助手:消息内容]
            列表内容让llm去形成摘要，拿到llm返回的content作为摘要
            摘要保存到[session_id， 摘要内容]
        输出：
           摘要内容summary 
        """
        history = self.get_short_term(session_id)
        messages = history.messages
        if len(messages) < 2:
            logger.info("消息太少，无需摘要", session_id=session_id)
            return ""

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

        self.medium_term[session_id] = summary

        return summary

    async def extract_long_term_memories(self, session_id: str) -> list[str]:
        """从会话中提取重要事实，存入长期记忆
        输入：
            session_id
        处理：
            短期记忆拿到历史，<4 返回空，否则将历史通过llm总结为历史会话列表，按照JSON数据格式返回
            ["记忆1", "记忆2", "记忆3", ...]
            JSON模块将JSON数据解析为python对象, 通过Chroma实例存入向量数据库
        输出： 
            历史会话内容，JSON数据格式
        """
        history = self.get_short_term(session_id)
        messages = history.messages

        if len(messages)<4:
            return []

        message_text = "\n".join([
            f"{'用户' if m.type=='human' else '助手'}: {m.content}"
            for m in messages
        ])

        prompt = f"""
        请从以下对话中提取值得长期记住的重要信息，格式为JSON数组：
        - 用户的个人信息（职业、背景、偏好等）
        - 用户明确表达的喜好、习惯、观点
        - 重要的事实和知识
        - 用户的目标和计划

        每条信息用一句话表述

        对话内容：
        {message_text[:2000]}

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
        """
            输入：
                用户query的问题，top_k向量要求
            处理：
                长期记忆处理：Chroma中通过query找到k个相似的向量page_content
                中期记忆处理: 拿到最新后3个medium_term的值列表构成中期记忆的summaries
            输出： 
                {"long_term": [], "summary": []}
        """
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

    def build_memory_context(self, query: str) -> str:
        # 构建上下文字符串，用于注入到prompt中
        # 输入是用户的query，根据用户的query，搜索最相关的的长期记忆和中期摘要
        """
        输入：
            用户query
        处理：
            通过用户的query，拿到相关长期记忆和中期记忆
        输出：
            返回长期记忆和中期记忆拼接成包含关于用户的已知信息和最近对话摘要的内容列表
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
