# 把后台复杂的检索服务，包装成AI Agent能够听懂并调用的工具
from langchain_core.tools import tool
from rag.retrieval.service import RetrievalStrategy, RetrievalService
from rag.tools.retrieval_tools import build_retrieval_tools as create_retrieval_toos

def build_retrieval_tools(retrieval_service:RetrievalService):

    @tool
    def semantic_search(query:str, top_k:int=5):
        """
        使用语义检索查找与问题语义相关的文档。
        适合自然语言问题、概念理解、同义表达
        """
        return retrieval_service.search(
            query=query,
            strategy=RetrievalStrategy.SEMANTIC,
            top_k=top_k,
        )

    @tool
    def keyword_search(query:str, top_k:int=5):
        """
        使用关键词检索
        适合产品型号、编号、专有名词、精确术语
        """
        return retrieval_service.search(
            query=query,
            strategy=RetrievalStrategy.KEYWORD,
            top_k=top_k,
        )

    @tool
    def hybird_search(query:str, top_k:int=5):
        """
        同时结合语义检索和关键词检索
        适合既需要语义理解，又包含关键术语的问题
        """
        return retrieval_service.search(
            query=query,
            strategy=RetrievalStrategy.HYBRID,
            top_k=top_k,
        )

    @tool
    def mmr_search(query:str, top_k:int=5):
        """
        使用MMR检索，在保证相关性的同时增加结果多样性
        适合需要从不同角度获取信息的问题
        """
        return retrieval_service.search(
            query=query,
            strategy=RetrievalStrategy.MMR,
            top_k=top_k,
        )

    return [
        semantic_search,
        keyword_search,
        hybird_search,
        mmr_search,
    ]