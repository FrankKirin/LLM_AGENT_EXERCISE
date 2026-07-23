from langchain_openai import ChatOpenAI
from core.config import settings
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from core.logger import logger

# 1 配置好模型
llm = ChatOpenAI(
    base_url=settings.LLM_BASE_URL,
    timeout=settings.LLM_TIMEOUT,
    api_key=settings.LLM_API_KEY,
    model = settings.LLM_MODEL,
    temperature=0.3
)

# 2 设置ChatPromptTemplate
prompt = ChatPromptTemplate(
    [
        ("system", "You are a helpful AI bot, you always think step by step"),
        ("human", "{user_query}")
    ]
)

# 3 定义好运行管道, prompt | llm | StrOutParser()
basic_chain = prompt | llm | StrOutputParser()

# 4 定义运行函数
async def func_run():
    # # 1.异步调用结果
    # res = await basic_chain.ainvoke({"user_query": "什么是ReAct智能体?"})
    # logger.info("异步调用结果", result=res)
    # print(res)

    # 2.异步流式输出
    print("\n==========异步流式输出==========")
    async for chunk in basic_chain.astream({"user_query":"解释一下AI Agent中工具调用的概念"}):
        print(chunk, end="")


if __name__ == "__main__":
    import asyncio
    asyncio.run(func_run())