# Query Understanding + Chroma检索编排

from typing import Any
from query_understanding import QueryContext, QueryUnderstandingService
from langchain_core.vectorstores import VectorStore

class RAGService:
    """
    """
    def __init__(
        self,
        query_understanding: QueryUnderstandingService,
        vector_store: VectorStore,
        top_k: int=4,
    ):
        self.query_understanding = query_understanding
        self.vector_store = vector_store
        self.top_k = top_k

    def query(
        self,
        user_query: str,
        context: QueryContext|None = None,
    ) -> dict[str, Any]:
        """执行问题理解、必要信息检查和向量检索。"""

        if context is None:
            context = QueryContext()

        # 1.理解用户问题
        # analysis返回一个QueryUnderstandingResult
        analysis = self.query_understanding.run(
            user_query=user_query,
            context=context
        )
        # 2.必要信息不足，直接返回追问
        if analysis.needs_clarification:
            return {
                "status": "clarification_required",
                "message": analysis.clarification_question,
                "documents": [],
                "context": analysis.next_context,
                "analysis": analysis,
            }
        # 3.准备Chroma检索参数
        # 一个tok_k，和一个自定义的search_kwargs
        search_kwargs = {
            "k": self.top_k,
        }
        if analysis.metadata_filter is not None:
            search_kwargs["filter"] = analysis.metadata_filter
        # 4.执行向量检索
        documents = self.vector_store.similarity_search(
            query=analysis.rewritten_query,
            **search_kwargs
        )
        # 5.返回检索结果
        return {
            "status": "retrieved" if documents else "no_documents",
            "message": None,
            "documents": documents,
            "context": analysis.next_context,
            "analysis": analysis,
            "rewritten_query": analysis.rewritten_query,
            "metadata_filter": analysis.metadata_filter,
        }