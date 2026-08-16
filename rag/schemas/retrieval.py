from typing import Any

from langchain_core.documents import Document
from pydantic import BaseModel, Field

class RetrievalResult(BaseModel):
    # 单个检索到的文档
    document: Document
    score: float | None = None
    rank: int
    strategy: str
    # 每次实例化retrievalResult时，确保每个对象都有独立的空字典
    metadata: dict[str, Any] = Field(default_factory=dict)

class RetrievalResponse(BaseModel):
    # 一次完整的检索响应
    query: str
    strategy: str
    results: list[RetrievalResult]