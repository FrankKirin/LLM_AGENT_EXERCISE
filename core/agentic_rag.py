"""
Agentic rag是将不同检索策略封装成工具，让智能体选择调用
对每种检索策略有明确的使用场景描述，引导只鞥难题正确选择
检索结果统一格式返回，包含文档内容、相似度、来源等元数据
用StructuredTool定义工具
"""
from core.rag_vector_store import get_retriever

# 一、统一检索结果格式
# 设计思路：所有检索策略返回统一格式，便于后续处理和评估
# 包含：文档内容、相似度分数、来源信息、元数据
def format_search_results(docs, stratege):
    """统一格式化检索结果"""
    # return为什么是list[dict], 参数docs为什么是list
    pass


# 二、定义不同检索工具
# 不同检索方法封装成一个独立函数，用StructuredTool.from_function包装
# description写清楚适用场景，方便智能体根据描述选择工具
# description写这个工具解决什么问题，不解决什么问题，什么时候应该调用
def semantic_search(query: str, k: int=4) -> str:
    """
    语义检索：基于向量相似度查找相关文档
    适用场景：概念性问题、模糊查询、需要理解语义的问题。
    例如："什么是AI Agent?“、”介绍一下LangGraph的原理”

    Args:
        query：检索查询
        k：返回文档数量，默认为4
    """
    retriever = get_retriever(k=k)
    docs = retriever.invoke(query)
    # 为什么return是json.dumps()?

def keyword_search():
    # 关键词搜索
    pass

def hybrid_search():
    pass

def mmr_search():
    pass

