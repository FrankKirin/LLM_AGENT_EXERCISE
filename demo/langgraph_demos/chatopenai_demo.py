from langchain_openai import ChatOpenAI
import asyncio


llm = ChatOpenAI(
    model="deepseek-ai/DeepSeek-V3.2",
    base_url="https://api.siliconflow.cn/v1",
    api_key="sk-ymzfgrasfojdodffsencbiwayqqedjhyttmizhhaadzotsks",
    streaming=True,
)

async def main():
    async for chunk in llm.astream("SQLalchemy中ORM是怎么用的？"):
        # print(chunk.content, flush=True)  # end是手动去掉了\n, flush是防止print缓冲，直接打印显示
        print(chunk.content, end="", flush=True)  # end是手动去掉了\n, flush是防止print缓冲，直接打印显示

asyncio.run(main())


