from rag.retrieval.base import BaseRetriever
from rag.schemas.retrieval import RetrievalResponse, RetrievalResult


class SemanticRetriever(BaseRetriever):

    def __init__(self, vector_store):
        self.vector_store = vector_store

    def search(
        self,
        query: str,
        top_k: int = 5,
        **kwargs,
    )-> RetrievalResponse:

        docs = self.vector_store.similarity_search(
            query,
            k = top_k,
        )

        results = [
            RetrievalResult(
                document=doc,
                rank=i+1,
                strategy="semantic",
                metadata=doc.metadata,
            )
            for i, doc in enumerate(docs)
        ]

        # 这里返会strategy的作用是什么, 在混合检索中跟踪到检索的向量来自哪种策略
        return RetrievalResponse(
            query=query,
            strategy="semantic",
            results=results,
        )

class KeywordRetriever(BaseRetriever):

    def __init__(self, bm25_retriever):
        self.bm25_retriever = bm25_retriever

    def search(
        self,
        query: str,
        top_k: int=5,
    )->RetrievalResponse:

        docs = self.bm25_retriever.invoke(query)

        docs = docs[:top_k]

        results = [
            RetrievalResult(
                document = doc,
                rank = i+1,
                strategy = "keyword",
                metadata = doc.metadata,
            )
            for i, doc in enumerate(docs)
        ]

        return RetrievalResponse(
            query=query,
            strategy="keyword",
            results = results,
        )

class MMRRetriever(BaseRetriever):

    def __init__(self, vector_store):
        self.vector_store = vector_store

    def search(
        self,
        query: str,
        top_k: int=5,
        fetch_k: int=20,
        lambda_mult: float=0.5,
        **kwargs,
    )->RetrievalResponse:

        docs = self.vector_store.max_marginal_relevance_search(
            query,
            k=top_k,
            fetch_k=fetch_k,
            lambda_mult=lambda_mult,
        )

        results = [
            RetrievalResult(
                document=doc,
                rank = i+1,
                strategy = "mmr",
                metadata = doc.metadata
            )
            for i, doc in enumerate(docs)
        ]

        return RetrievalResponse(
            query=query,
            strategy="mmr",
            results=results,
        )

class HybridRetriever(BaseRetriever):

    def __init__(
        self,
        semantic_retriever: SemanticRetriever,
        keyword_retriever: KeywordRetriever,
    ):
        self.semantic_retriever = semantic_retriever
        self.keyword_retriever = keyword_retriever


    def search(
        self,
        query: str,
        top_k: int=5,
        **kwargs,
    ) -> RetrievalResponse:

        # 位置参数和关键字参数可以混用，前提是位置参数必须在前
        semantic_result = self.semantic_retriever.search(
            query,
            top_k = top_k,
        )
        keyword_result = self.key_word_retriever.search(
            query,
            top_k = top_k,
        )

        merged = self._merge_results(
            semantic_result.results,
            keyword_result.results,
            top_k,
        )

        return RetrievalResponse(
            query=query,
            strategy="hybird",
            results=merged,
        )

    def _merge_results(
        self,
        semantic_results: list[RetrievalResult],
        keyword_results: list[RetrievalResult],
        topk: int,
    ) -> list[RetrievalResult]:

        results = []
        seen = set()

        for item in semantic_results+keyword_results:
            # 用metadata中的chunk_id或者document下的page_content
            ele = item.document.metadata.get("chunk_id", item.document.page_content)

            if ele not in seen:
                results.append(item)
                if len(results) >= topk:
                    break
            seen.add(ele)

        return results