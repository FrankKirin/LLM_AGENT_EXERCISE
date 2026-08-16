from pathlib import Path
from functools import lru_cache
from langchain_openai import OpenAIEmbeddings
from core.config import settings
from langchain_chroma import Chroma
from core.logger import logger
from langchain_community.document_loaders import PyMuPDFLoader, TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.retrievers import BM25Retriever
from langchain_core.documents import Document
from langchain_classic.retrievers import EnsembleRetriever
from typing import Literal
from langchain_core.retrievers import BaseRetriever
from rich import print

# 配置好硅基流动的embedding模型
embedding = OpenAIEmbeddings(
    base_url=settings.LLM_EMBEDDING_BASE_URL,
    api_key=settings.LLM_EMBEDDING_API_KEY,
    model=settings.LLM_EMBEDDING_MODEL
)

CHUNK_SIZE = 1000
CHUNK_OVERLAP = 200

# 递归尝试不同字符进行分割，找到一个有效的分割方式
text_splitter = RecursiveCharacterTextSplitter(
    chunk_size = CHUNK_SIZE,
    chunk_overlap = CHUNK_OVERLAP,
    separators = ["\n\n", "\n", "。", "，", "！", "？", " ", "", "；"],
    length_function = len
)

def load_pdf(file_path: str):
    loader = PyMuPDFLoader(file_path)
    docs = loader.load()
    logger.info(f"加载PDF原始页数：{len(docs)}")
    return text_splitter.split_documents(docs)

def load_txt(file_path: str):
    loader = TextLoader(file_path)
    docs = loader.load()
    return text_splitter.split_documents(docs)

# 本地持久化向量库
CHROMA_DIR = Path(__file__).resolve().parent.parent/"core"/"chroma_db"
GLOBAL_VECTOR_STORE = Chroma(
    persist_directory=str(CHROMA_DIR),
    embedding_function=embedding
)

def get_vector_store() -> Chroma:
    """获取或创建Chroma数据库实例"""
    return GLOBAL_VECTOR_STORE

def add_documents_to_vector(docs):
    """批量写入向量库"""
    db = get_vector_store()
    db.add_documents(docs)
    logger.info(f"成功写入{len(docs)}块文档到向量库")


def init_pdf_file_to_vector(file_name: str):
    from pathlib import Path
    # resolve将文件的相对路径转为绝对路径
    PROJECT_ROOT = Path(__file__).resolve().parent.parent
    # PROJECT_ROOT是个PosixPath对象, 拼接直接用/
    file_loc = PROJECT_ROOT / "data" / file_name

    doc_list = load_pdf(str(file_loc))
    add_documents_to_vector(doc_list)

def get_vector_retriever(
    k: int=4, 
    search_type:Literal["similarity", "mmr"] = "similarity",
    fetch_k: int=20,    # 候选池中含多少数量
    lambda_mult: float = 0.5,   # 多样性和相关性权重
) -> BaseRetriever:
    """构造检索器, 召回检索内容
       支持语义检索和mmr检索 
    """
    db = get_vector_store()

    search_kwargs = {"k": k}

    if search_type == "mmr":
        search_kwargs.update({"fetch_k": fetch_k, "lambda_mult": lambda_mult})

    return db.as_retriever(
        search_type = search_type,
        search_kwargs = search_kwargs
    )

def get_bm25_retriever(k:int=4)->BaseRetriever:
    vector_store = get_vector_store()
    all_data = vector_store.get(include=["documents", "metadatas"])
    retriever = BM25Retriever.from_documents(all_data]))
    retriever.k = k

    return retriever

def get_hybrid_retriever(k: int=4)->BaseRetriever:
    """
    输入：
        指定retriever返回的Document数k
    处理：
        获取普通retriever和bm25_retriever
        通过EnsembleRetriever拼接两个retriever，配置权重
    输出：
        hybird retriever
    """
    sementic_retriever = get_vector_retriever(search_type="similarity")
    bm25_retriever = get_bm25_retriever(k=4)

    hybird_retriever =  EnsembleRetriever(
        retrievers = [sementic_retriever, bm25_retriever],
        weights = [0.5, 0.5]
    )
    return hybird_retriever


def test_mmr_search(query:str, k=5, search_type="mmr", fetch_k=20):
    retriever = get_vector_retriever(search_type=search_type, k=k, fetch_k=fetch_k)
    docs = retriever.invoke(query)
    logger.info(f"检索到的内容{docs}")
    assert docs, "搜索不到query相关内容"
    assert len(docs) <= 5, "检索到的向量数量不符合"
    logger.info("✅mmr search测试通过")
    

def test_bm25_search(query, k):
    retriever = get_bm25_retriever(k)
    result = retriever.invoke(query)
    logger.debug(f"bm25 retriever result: {result}")
    assert result, "搜索不到query相关内容"
    assert len(result) <= 4, "检索到的向量数量不符合"
    logger.info(f"✅bm256_search测试通过")

def test_hibird_retriever(query, k):
    retriever = get_hybrid_retriever(k)
    docs = retriever.invoke(query)

    assert docs, "混合检索未检索到内容"
    logger.debug(f"The result of {docs}")
    logger.info(f"✅hibird_search测试通过")


if __name__ == "__main__":
    query = "用户有什么兴趣爱好或者偏好？"
    # test_mmr_search(query=query)
    # test_bm25_search(query, k=4)
    # test_hibird_retriever(query, k=4)
    result = get_vector_store()
    print(result[:3])
