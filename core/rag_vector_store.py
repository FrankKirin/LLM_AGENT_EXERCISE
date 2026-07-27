from langchain_openai import OpenAIEmbeddings
from core.config import settings
from langchain_chroma import Chroma
from core.logger import logger

embedding = OpenAIEmbeddings(
    base_url=settings.LLM_EMBEDDING_BASE_URL,
    api_key=settings.LLM_EMBEDDING_API_KEY,
    model=settings.LLM_EMBEDDING_MODEL
)

# 本地持久化向量库
CHROMA_DIR = "./chroma_db"

def get_vector_store():
    """获取或创建Chroma数据库实例"""
    return Chroma(
        persist_directory=CHROMA_DIR,   # 实现了磁盘持久化，避免每次重置程序都要重新生成embedding
        embedding_function=embedding    
    )

def add_documents_to_vector(docs):
    """批量写入向量库"""
    db = get_vector_store()
    db.add_documents(docs)
    logger.info(f"成功写入{len(docs)}块文档到向量库")

def get_retriever(k=4):
    """构造检索器"""
    db = get_vector_store()
    return db.as_retriever(
        search_type="similarity",
        search_kwargs = {"k":k}
    )

if __name__ == "__main__":
    from langchain_core.documents import Document

    print("========= 1. 构造测试文档  ========")
    test_docs = [
        Document(
            page_content="韩电冰箱的整机保修期为 1 年，压缩机等主要部件保修 3 年。",
            metadata={"source": "manual.pdf", "page":1}
        ),
        Document(
            page_content="若冰箱制冷效果差，请检查门封条是否密封不严或温控档位是否设置过低。",
            metadata={"source": "manual.pdf", "page":5}
        ),
        Document(
            page_content="LangChain 是一个用于构建 LLM 驱动的大模型应用的开发框架。",
            metadata={"source": "tech_doc.pdf", "page":1}
        )
    ]

    # 测试批量写入
    add_documents_to_vector(test_docs)

    # 查看向量库总记录数
    vector_store = get_vector_store()
    doc_count = vector_store._collection.count()
    print(f"当前Chroma向量库中共有 {doc_count}条数据")

    # 测试向量检索功能
    retriever = get_retriever(k=2)

    print("====测试相关关问题检测效果=====")
    query_1 = "冰箱保修多久？"
    results_1 = retriever.invoke(query_1)
    for i, doc in enumerate(results_1):
        print(f"[结果 {i+1}]内容：{doc.page_content} | 元数据: {doc.metadata}")

    # 测试无关问题的检索效果
    print("====测试无关问题检测效果=====")
    query_2 = "Kimi K3是什么模型？"
    results_2 = retriever.invoke(query_2)
    for i, doc in enumerate(results_2):
        print(f"[结果{i+1}内容：{doc.page_content} | 元数据：{doc.metadata}")