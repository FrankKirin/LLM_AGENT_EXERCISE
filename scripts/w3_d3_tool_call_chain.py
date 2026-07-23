from core.config import settings
from langchain_core.prompts import MessagesPlaceholder, ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough
from langchain_openai import ChatOpenAI
from core.new_tools import tools
from core.logger import logger

# 创建了llm
llm = ChatOpenAI(
    base_url=settings.LLM_BASE_URL,
    api_key=settings.LLM_API_KEY,
    model=settings.LLM_MODEL,
    temperature=0.3,
    timeout=settings.LLM_TIMEOUT
)

# prompt构建,差点忘记！！！
prompt = ChatPromptTemplate([
    MessagesPlaceholder("history"),
    ("system", "你是工单智能助手，可以调用工具查询数据"),
    ("human", "{input}")
])

# 绑定工具
llm_with_tools = llm.bind_tools(tools)

# 配置调用链路
chain = RunnablePassthrough() | prompt | llm_with_tools

# 调用工具
async def use_chain():
    res = await chain.ainvoke(
        {"history":[],"input":"查询OD20260701工单"}
    )
    logger.debug("The result of chain_with_tool", res=res)    
    logger.debug("工具参数调用", res=res.tool_calls)

if __name__ == "__main__":
    import asyncio
    asyncio.run(use_chain())
