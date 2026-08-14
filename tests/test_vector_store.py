# 脚本底部临时验证代码秦阿姨单元测试，改用pytest框架，用断言替代手动print，实现测试环境隔离
# 测试文件名必须以test_开头，这样测试框架才能识别
import pytest
from langchain_core.documents import Document
from core.rag_vector_store import add_documents_to_vector, get_vector_retriever, get_vector_store

if __name__ == "__main__":
    from langchain_core.documents import Document

    print("========= 1. 构造测试文档  ========")
    test_docs = [
        Document(
            page_content="韩电冰箱的整机保修期为 1 年，压缩机等主要部件保修 3 年。",
            metadata={"source": "manual.pdf", "page":1}
        ),
        Document(
            page_content="若冰箱制冷效果差，请检查门封条是否密封不严或温控档位是否设置过低。",
            metadata={"source": "manual.pdf", "page":5}
        ),
        Document(
            page_content="LangChain 是一个用于构建 LLM 驱动的大模型应用的开发框架。",
            metadata={"source": "tech_doc.pdf", "page":1}
        )
    ]

    # 测试批量写入
    add_documents_to_vector(test_docs)

    # 查看向量库总记录数
    vector_store = get_vector_store()
    doc_count = vector_store._collection.count()
    print(f"当前Chroma向量库中共有 {doc_count}条数据")

    # 测试向量检索功能
    retriever = get_vector_retriever(k=2)

    print("====测试相关关问题检测效果=====")
    query_1 = "冰箱保修多久？"
    results_1 = retriever.invoke(query_1)
    for i, doc in enumerate(results_1):
        print(f"[结果 {i+1}]内容：{doc.page_content} | 元数据: {doc.metadata}")

    # 测试无关问题的检索效果
    print("====测试无关问题检测效果=====")
    query_2 = "Kimi K3是什么模型？"
    results_2 = retriever.invoke(query_2)
    for i, doc in enumerate(results_2):
        print(f"[结果{i+1}内容：{doc.page_content} | 元数据：{doc.metadata}")