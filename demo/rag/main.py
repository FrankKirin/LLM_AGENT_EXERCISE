# main.py
from core.lc_baseline import llm
from core.rag_vector_store import get_vector_store

from query_understanding import (
    QueryContext,
    QueryUnderstandingService,
)
from rag_service import RAGService

vector_store = get_vector_store()


# 当前知识库没有建立 product_brand、product_model Metadata。
# 因此先不启用这两个过滤字段。
query_understanding = QueryUnderstandingService(
    llm=llm,
    enabled_metadata_fields=set(),
)

rag_service = RAGService(
    query_understanding=query_understanding,
    vector_store=vector_store,
    top_k=4,
)

# 一段对话只初始化一次上下文
context = QueryContext()

# 第一轮：用户没有提供产品型号
result = rag_service.query(
    user_query="这款冰箱具体应该怎么设置化霜模式？",
    context=context,
)

print("状态：", result["status"])
print("回复：", result["message"])

# 保存本轮上下文
context = result["context"]

# 假设用户看到追问后，回复：
# BCD-500
if result["status"] == "clarification_required":

    result = rag_service.query(
        user_query="BCD-500",
        context=context,
    )

    context = result["context"]

    print("第二轮状态：", result["status"])
    print("改写后的 Query：", result.get("rewritten_query"))

    for document in result["documents"]:
        print(document.page_content)