from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from core.logger import logger
from core.config import settings
from langchain_core.runnables import RunnablePassthrough
# from langchain_core.prompts import Str
from langchain_core.output_parsers import StrOutputParser

# 定义llm
llm = ChatOpenAI(
    base_url=settings.LLM_BASE_URL,
    api_key = settings.LLM_API_KEY,
    model = settings.LLM_MODEL,
    timeout = settings.LLM_TIMEOUT,
    temperature=0.3
)

# 定义prompt
prompt = ChatPromptTemplate.from_messages(
    [
    ("system","你是一个专业的B端AI助手, 回答问题简单严谨"), # 2元tuple中间用 , 分隔
    MessagesPlaceholder("history"),
    ("human","{input}")
    ]
)

# 定义chain,chain中的类都需要通过类名+()实现实例化
chain = (
    RunnablePassthrough()
    | prompt
    | llm
    | StrOutputParser()
)

# 定义运行的函数
async def main():
    res = await chain.ainvoke({"input": "什么是ReAct?", "history":[]})
    logger.info("The result of chain:", res=res)
    return None

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())