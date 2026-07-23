from langchain_core.chat_history import InMemoryChatMessageHistory
from langchain_core.messages import HumanMessage, AIMessage

# 做了个记忆组件类，实现方法用于添加用户记忆和AI记忆
class ChatMemoryManager:
    """
    保存或创建已经有session_id的用户
    异步保存HumanMessage和AIMessage
    """
    def __init__(self):
        # store字典按照session_id: InMemoryChatMessageHistory
        self.store = {}

    def get_history(self, session_id: str)->InMemoryChatMessageHistory:
        # 不在store就在store中创建，在的话直接返回
        if session_id not in self.store:
            self.store[session_id] = InMemoryChatMessageHistory()
        return self.store[session_id]

    async def add_AIMessage(self, session_id:str, content:str):
        # 有历史就会拿到历史，没有历史就拿到空
        history = self.get_history(session_id)
        # 只是把消息追加进历史，不返回任何消息
        await history.aadd_messages([AIMessage(content=content)])

    async def add_HumanMessage(self, session_id:str, content:str):
        history = self.get_history(session_id)
        await history.aadd_messages([HumanMessage(content=content)])


memory_manager = ChatMemoryManager()