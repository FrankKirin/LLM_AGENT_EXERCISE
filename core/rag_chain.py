from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.runnables import RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser
from core.config import settings
from core.rag_vector_store import get_retriever
from core.logger import logger

# 创建ChatOpenAI客户端
llm = ChatOpenAI(
    base_url=settings.LLM_BASE_URL,
    model=settings.LLM_MODEL,
    api_key=settings.LLM_API_KEY,
    temperature=0.1,
)

# 塞入企业级RAG prompt
rag_prompt = ChatPromptTemplate.from_messages([
    ("system","""
你是企业私有知识库问答助手。
严格**仅根据参考文档内容回答**。
如果文档没有相关信息，直接回答 【暂无相关信息】，禁止编造，禁止幻觉。
禁止自己发挥，禁止连续梁，禁止拼接外部知识

参考文档：
{context}
"""),
    ("human", "{question}")
])


# 构建Runnable管道
retriever = get_retriever() # 拿到List[Document]

def format_docs(docs):
    return "\n\n".join([d.page_content for d in docs])

rag_chain = (
    # 内容进来后会并行发给两条路径
    {"context":retriever | format_docs, "question": RunnablePassthrough()}
    | rag_prompt
    | llm
    | StrOutputParser()
)

# 带历史对话的RAG
contextual_prompt = ChatPromptTemplate.from_messages([
    ("system", "根据对话历史，重构用户问题，使其具备独立语义，不要回答问题，只输出重构后的问题"),
    MessagesPlaceholder("history"),     # 动态插入历史
    ("human", "{question}")
])
# 问题重构链
rewrite_chain = contextual_prompt | llm | StrOutputParser()

async def chat_rag_chain(history, question):
    # Step1.重构问题
    new_question = rewrite_chain.invoke({"history": history, "question": question})
    # Step2. 检索+回答
    return rag_chain.ainvoke(new_question)


if __name__ == "__main__":
    print("="*20 + "开始RAG链路测试" + "="*20)

    # case1:知识库中有答案
    logger.debug("冰箱保修多久？")
    test_query_1 = "冰箱保修多久？"
    response_1 = rag_chain.invoke(test_query_1)
    logger.debug(f"AI 回答：\n{response_1}")

    # case2:幻觉边界测试（知识库里绝对没有的信息）
    logger.debug("宇宙的起源是什么？")
    test_query_2 = "宇宙的起源是什么？"
    response_2 = rag_chain.invoke(test_query_2)
    logger.debug(f"AI 回答：\n{response_2}")

    # case3:打印机流式输出测试
    logger.debug("冰箱制冷效果差怎么处理？")
    test_query_3 = "冰箱制冷效果差怎么处理？"
    response_3 = rag_chain.invoke(test_query_3)
    logger.debug(f"AI 回答：\n{response_2}")
    # LCEL天然支持.stream()方法，不需要修改链的内部定义
    for chunk in rag_chain.stream(test_query_3):
        # end=""表示不换行，flush表示不缓冲，直接输出
        # print(chunk, end="", flush=True)
        print(chunk, flush=True)