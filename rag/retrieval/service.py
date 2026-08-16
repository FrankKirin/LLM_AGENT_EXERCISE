from enum import Enum

from rag.retrieval.base import BaseRetriever
from rag.schemas.retrieval import RetrievalResponse

class RetrievalStrategy(str, Enum):
    # 职责分离：相当于一本“菜单”
    SEMANTIC = "semantic",
    KEYWORD = "keyword",
    HYBRID = "hybrid",
    MMR = "mmr"

class RetrievalService:
    # 相当于后厨
    def __init__(
        self,
        semantic_retriever: BaseRetriever,
        keyword_retriever: BaseRetriever,
        hybrid_retriever: BaseRetriever,
        mmr_retriever: BaseRetriever,
    ):
        self._retrievers = {
            RetrievalStrategy.SEMANTIC: semantic_retriever,
            RetrievalStrategy.KEYWORD: keyword_retriever,
            RetrievalStrategy.HYBRID: hybrid_retriever,
            RetrievalStrategy.MMR: mmr_retriever,
        }

    def search(
        self,
        query: str,
        strategy: RetrievalStrategy,
        top_k: int=5,
        **kwargs,
    ) -> RetrievalResponse:

        retriever = self._retrievers.get(strategy)

        if retriever is None:
            raise ValueError(
                f"Unsupported retrieval strategy: {strategy}"
            )

        return retriever.search(
            query=query,
            top_k=top_k,
            **kwargs,
        )