# Chroma实例
# Embedding
# 持久化路径
from pathlib import Path
from functools import lru_cache
from langchain_openai import OpenAIEmbeddings
from core.config import settings
from langchain_chroma import Chroma
from core.logger import logger
from langchain_community.document_loaders import PyMuPDFLoader, TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter

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
