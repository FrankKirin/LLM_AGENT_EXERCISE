from langchain_core.retrievers import BaseRetriever
from langchain_community.retrievers import BM25Retriever
from langchain_core.documents import Document
from typing import Literal

def get_vector_retriever(
    vector_store,
    k: int = 4,
    search_type: Literal["mmr", "similarity"] = "similarity",
    fetch_k: int = 20,
    lambda_mult: float = 0.5
) -> BaseRetriever:

    search_kwargs = {"k": k}

    if search_type == "mmr":
        search_kwargs.update({
            "lambda_mult": lambda_mult,
            "fetch_k": fetch_k
        })

    return vector_store.as_retriever(
        search_type = search_type,
        search_kwargs = search_kwargs,
    ) 

def get_bm25_retriever(
    documents: list[Document],
    k: int=4
) -> BM25Retriever:
    """
        输入：

        处理：

        输出： 
    """
    retriever = BM25Retriever.from_documents(documents)
    retriever.k = k

    return retriever

def load_documents_from_vector_store(vector_store):
    data = vector_store.get(
    )


    pass
