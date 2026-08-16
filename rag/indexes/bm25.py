# BM25 index
# 文档加载
from collections.abc import Sequence
# from typing import Sequence 过渡产物不再推荐
from langchain_core.documents import Document
from langchain_community.retrievers import BM25Retriever

def build_bm25_retriever(documents: Sequence[Document], top_k:int=4) -> BM25Retriever
    # 构建一个简易的BM25检索器
    if not documents:
        raise ValueError("documents 不能为空")

    # BM25Retriever会自动完成文档的Tokenization和BM25 Index
    retriever = BM25Retriever.from_documents(
        list(documents)
    )

    retriever.k = top_k

    return retriever
