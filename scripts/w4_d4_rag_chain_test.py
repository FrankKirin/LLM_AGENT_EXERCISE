from core.rag_chain import rag_chain
import asyncio

async def test_rag():
    res = await rag_chain.ainvoke("这个文档主要讲了什么内容？")
    print("RAG回答 ", res)

if __name__ == "__main__":
    asyncio.run(test_rag())