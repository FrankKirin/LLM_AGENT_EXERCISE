from rag.retrieval.vector_retriever import (
    SemanticRetriever, KeywordRetriever, HybridRetriever, MMRRetriever
)
from rag.retrieval.service import RetrievalService
from rag.vectorstore import get_vector_store
# from rag.
from rag.tools.retrieval_tools import build_retrieval_tools as create_retrieval_tools

def build_retrieval_service() -> RetrievalService:
    semantic_retriever = SemanticRetriever(
        vector_store = get_vector_store()
    )

    # keyword_retriever = KeywordRetriever(
    #     bm25_retriever = bm25_retriever
    # )

    mmr_retriever = MMRRetriever(
        vector_store=get_vector_store()
    )

    hybird_retriever = HybridRetriever(
        semantic_retriever=get_vector_store()
        keyword_retriever=keyword_retriever()
    )


    return RetrievalService(
        semantic_retriever=semantic_retriever,
        # keyword_retriever=keyword_retriever
        hybrid_retriever=hybird_retriever,
        mmr_retriever=mmr_retriever,
    )

def build_retrieval_tools():
    retrieval_service = build_retrieval_service()

    return create_retrieval_tools(
        retrieval_service
    )