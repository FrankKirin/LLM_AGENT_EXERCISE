from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import PyMuPDFLoader, TextLoader
from core.logger import logger


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


if __name__ == "__main__":
    from pathlib import Path
    PROJECT_ROOT = Path(__file__).resolve().parent.parent
    file_path = PROJECT_ROOT/"data/P10上下水套装版说明书.pdf"

    logger.debug("PDF文件路径", path=file_path)

    chunks = load_pdf(file_path)
    logger.info(f"最终分块数量：{len(chunks)}")
    logger.info("首块内容", content=chunks[0].page_content[:200])