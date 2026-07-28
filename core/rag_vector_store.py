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
    """构造检索器, 召回检索内容"""
    db = get_vector_store()
    return db.as_retriever(
        search_type="similarity",
        search_kwargs = {"k":k}
    )
