from langchain_openai import ChatOpenAI
from new_tools import tools
from core.config import settings
from core.chat_memory import memory_manager

# 创建LLM并绑定tools
llm = ChatOpenAI(
    base_url = settings.LLM_BASE_URL,
    model = settings.LLM_MODEL,
    api_key = settings.LLM_API_KEY,
    temperature = 0.1,
    timeout = settings.LLM_TIMEOUT
).bind_tools(tools)

# 实现ReAct循环 输入用户session_id和用户问题 输出工具调用 拼接会话历史和用户新问题 最多调用3次
# 处理无工具调用场景
# 处理有工具调用场景

async def run_react_agent(session_id: str, user_query: str):
    history = memory_manager.get_history(session_id=session_id).messages
