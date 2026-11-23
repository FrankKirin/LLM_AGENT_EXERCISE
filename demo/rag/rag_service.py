# Query Understanding + Chroma检索编排

from query_understanding import QueryContext, QueryUnderstandingService
from langchain_core.vectorstores import VectorStore


class RAGService:
    def __init__(
        self,
        query_understanding: QueryUnderstandingService,
        vector_store: VectorStore,
        top_k: int=4,
    )