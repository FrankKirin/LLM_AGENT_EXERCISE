"""
Agentic rag是将不同检索策略封装成工具，让智能体选择调用
对每种检索策略有明确的使用场景描述，引导只鞥难题正确选择
检索结果统一格式返回，包含文档内容、相似度、来源等元数据
用StructuredTool定义工具
"""
import json
import operator
from core.config import settings
from core.rag_vector_store import get_retriever
from langchain_core.tools import StructuredTool
from langgraph.prebuilt import ToolNode
from typing import TypedDict, Annotated
from langgraph.graph import StateGraph, END, START
from langchain.messages import AnyMessage, SystemMessage, HumanMessage, ToolMessage, AIMessage
from langgraph.checkpoint.memory import MemorySaver
from core.lc_baseline import llm
from core.logger import logger

# 一、统一检索结果格式
# 设计思路：所有检索策略返回统一格式，便于后续处理和评估
# 包含：文档内容、相似度分数、来源信息、元数据
def format_search_results(docs: list, strategy: str)->list[dict]:
    """统一格式化检索结果"""
    res = []
    for i, doc in enumerate(docs):
        res.append({
            "rank": i+1,
            "content": doc.page_content[:500],
            "metadata": doc.metadata,
            "strategy": strategy
        })
    return res

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
        query: 检索查询
        k: 返回文档数量，默认为4
    """
    retriever = get_retriever(k=k)
    docs = retriever.invoke(query)
    results = format_search_results(docs, "semantic")

    # ensure_ascii=False能够实现原生中文文本的输出
    # indent=2，美化输出格式，每层嵌套缩进2空格，并自动换行排版
    return json.dumps(results, ensure_ascii=False, indent=2)

def keyword_search(query: str, k: int=4)->str:
    """
    关键词检索：基于关键词精确匹配查找文档。
    适用场景：精确术语、代码、人名、特定名词、需要精准匹配的问题。
    例如：“ReAct算法的具体步骤”、“LangGraph的StateGraph怎么用”

    Args:
        query: 检索查询（建议用关键词组合）
        k: 返回文档数量, 默认4
    """
    # 简化实现：用语义检索模拟，实际生产用BM25等关键词
    retriever = get_retriever(k=k)
    docs = retriever.invoke(query)
    results = format_search_results(docs, "keyword")
    return json.dumps(results, ensure_ascii=False, indent=2)

def hybrid_search(query: str, k: int=4)->str:
    """
    混合检索：结合语义和关键词的检索方式
    适用场景：复杂问题、既需要语义理解又需要关键词精准匹配
    例如：“对比LangGraph和AutoGen的架构差异” 

    Args:
        query: 检索查询
        k: 返回文档数量，默认为4
    """
    retriever = get_retriever(k=k)
    docs = retriever.invoke(query)
    results = format_search_results(docs, "hybrid")
    return json.dumps(results, ensure_ascii=False, indent=2)

def mmr_search(query:str, k: int=4)->str:
    """
    MMR多样性检索：在相关性基础上增加多样性，避免结果过于相似。
    适用场景：需要广泛信息、多角度观点、调研类问题

    Args:
        query: 检索查询
        k: 返回文档数量，默认4
    """
    retriever = get_retriever(k=k)
    docs = retriever.invoke(query)
    results = format_search_results(docs, "mmr")
    return json.dumps(results, ensure_ascii=False, indent=2)

retrieval_tools = [
    StructuredTool.from_function(semantic_search),
    StructuredTool.from_function(keyword_search),
    StructuredTool.from_function(hybrid_search),
    StructuredTool.from_function(mmr_search),
]

# 智能体 系统提示词
# 明确告知智能体的角色、任务、工作流程
# 强调：先思考用什么检索策略 -> 检索 -> 评估结果 -> 不满意就换策略
AGENTIC_RAG_PROMPT = """
你是一个专业的研究助手，擅长通过检索知识库来回答复杂问题。

## 你的工作流程
1.分析用户问题，判断最适合的检索策略
2.选择合适的检索工具进行检索
3.评估检索结果是否足够回答问题
4.如果结果不够：
    - 换一种检索策略再试
    - 优化检索关键词再试
5.如果结果足够，综合所有检索结果，给出完整答案

## 检索工具选择指南
- 概念性/模糊问题 -> semantic_search
- 精确术语/代码/名词 -> keyword_search
- 复杂对比/分析问题 -> hybrid_search
- 调研类/需要广泛信息 -> mmr_search

## 重要规则
- 最多检索3次， 不要无限循环
- 每次检索后要评估结果质量
- 如果3次检索后结果仍不满意，如实说明信息不足
- 答案必须基于检索到的文档，不要编造
- 回答时注明信息来源的文档片段
""".strip()


"""
支持查询重写的智能体：
查询重写有这些好处：
1.从长问题中提取关键词
2.指代消解，明白用户query中比如它实际指的是什么
3.查询拓展：补充同义词，相关术语
4.查询分解：把复杂问题拆成多个子查询

LangGraph图构建
1.查询重写，优化检索词
2.工具检索调用节点
3.结果评估节点,判断是否满意
4.路由节点：评估满意->生成答案，不满意->继续检索
5.生成最终答案节点
"""

class AgenticRAGState(TypedDict):
    messages: Annotated[list[AnyMessage], operator.add]
    original_query: str
    current_query: str
    retrieval_count: int
    max_retrievals: int
    is_satisfied: bool
    final_answer: str

"""
查询重写节点
第一次检索前重写一次，后续每轮不满意也可以重写
智能体根据历史检索结果和评估反馈，优化查询词
用LLM生成更精准的检索词
"""
async def query_rewrite_node(state: AgenticRAGState):
    if state["retrieval_count"] == 0:
        prompt = f"""
        请将以下用户问题改写为更适合知识库检索的查询词。
        要求:
        1.提取核心关键词
        2.补充相关术语和同义词
        3.去除口语化表达
        4.输出纯文本查询，不要解释

        用户问题： {state['original_query']}
        """
    else:
        # 后续重写：基于历史检索结果
        # else语句几乎是走不到的，三元防御代码
        history = state["messages"][-1].content if state["messages"] else ""
        prompt = f"""
        之前的检索结果不够理想，请优化查询词重新检索。
        要求：
        1.分析之前检索结果的不足
        2.调整关键词，换个角度描述
        3.可以增加或减少关键词
        4.输出纯文本查询词，不要解释

        原问题：{state["original_query"]}
        上一次查询：{state["current_query"]}
        上一次检索结果反馈：{history[-200:] if history else '无'}
        """
    response = await llm.ainvoke(prompt)
    new_query = response.content.strip()

    logger.debug("llm改写后的new query content:", new_query=new_query)

    return {
        "current_query": new_query,
        "messages": [AIMessage(content=f"查询已重写为: {new_query}")]
    }

async def agent_reasoning_node(state: AgenticRAGState):
    """智能体推理节点：决定调用哪个检索工具"""
    system_msg = SystemMessage(content=AGENTIC_RAG_PROMPT)
    human_msg = HumanMessage(content=f"""
    请检索以下问题的相关信息：
    {state['current_query']}

    已检索次数：{state["retrieval_count"]} / {state["max_retrievals"]}

    注意：选择最合适的检索工具进行检索
    """)

    messages = [system_msg, human_msg]

    llm_with_tools = llm.bind_tools(retrieval_tools)
    response = await llm_with_tools.ainvoke(messages)

    logger.debug("response in agent reasoning", response=response)

    return {"messages": [response]}

# 结果评估节点
# 评估检索结果是否足够回答问题
# 评估维度：相关性、完整性、可信度
# 输出满意/不满意的判断，用于条件路由
async def evaluate_results_node(state: AgenticRAGState):
    # 拿到最后一条工具消息
    last_tool_msg = None
    for msg in reversed(state["messages"]):
        if hasattr(msg, "tool_call_id"):
            last_tool_msg = msg
            break

    # 如果没有发现有效的工具返回消息，跳过LLM评估打分流程，直接标记本次检索为“不满意”
    # 异常防御兜底与状态计数机制
    if not last_tool_msg:
        return {"is_satisfied": False, "retrieval_count": state["retrieval_count"]+1}

    prompt = f"""
    请评估以下检索结果是否足够回答用户的问题。

    用户问题：{state['original_query']}

    检索结果:
    {last_tool_msg.content[:1000]}

    请回答：
    1.结果是否相关？（是/否）
    2.信息是否足够回答问题？(是/否)
    3.是否需要继续检索？(是/否)

    只回答“满意”或“不满意”。
    """
    response = await llm.ainvoke(prompt)
    is_satisfied = "满意" in response.content and "不满意" not in response.content

    logger.debug("evaluate_results node中", is_satisfied=is_satisfied, res=response)

    return {
        "is_satisfied": is_satisfied,
        "retrieval_count": state["retrieval_count"] + 1
    }

async def generate_answer_node(state: AgenticRAGState):
    """综合所有检索结果，生成最终答案"""
    all_docs = []
    for msg in state["messages"]:
        if hasattr(msg, "tool_call_id"):
            all_docs.append(msg.content)

    docs_text = "\n\n".join(all_docs)

    prompt = f"""
    请根据以下检索到的文档，回答用户的问题

    用户问题：{state["original_query"]}

    检索到的文档：{docs_text[:3000]}

    要求：
    1.答案必须基于文档内容，不要编造
    2.结构清晰，分点回答
    3.如有不确定的地方，注明
    """
    response = await llm.ainvoke(prompt)

    logger.debug("generate answer content", res=response.content)

    return {
        "final_answer": response.content,
        "messages": [AIMessage(content=response.content)]
    }

def route_after_evaluation(state: AgenticRAGState):
    if state["is_satisfied"]:
        return "generate_answer"
    # 不满意的情况，没到达最大次数，继续检索
    if state["retrieval_count"] >= state["max_retrievals"]:
        return "generate_answer"
    return "query_rewrite"

def build_agentic_rag_graph():
    workflow = StateGraph(AgenticRAGState)

    workflow.add_node("query_rewrite", query_rewrite_node)
    workflow.add_node("agent_reasoning", agent_reasoning_node)
    workflow.add_node("retrieval_tools", ToolNode(retrieval_tools))
    workflow.add_node("evaluate_results", evaluate_results_node)
    workflow.add_node("generate_answer", generate_answer_node)

    workflow.add_edge(START, "query_rewrite")
    workflow.add_edge("query_rewrite", "agent_reasoning")
    workflow.add_edge("agent_reasoning", "retrieval_tools")
    workflow.add_edge("retrieval_tools", "evaluate_results")
    workflow.add_conditional_edges(
        "evaluate_results",
        route_after_evaluation,
        ["query_rewrite", "generate_answer"]
    )
    workflow.add_edge("generate_answer", END)

    checkpointer = MemorySaver()

    return workflow.compile(checkpointer=checkpointer)

if __name__ == "__main__":
    import asyncio

    query = "介绍一下石头扫地机器人P10的充电方式"
    graph = build_agentic_rag_graph()

    print(graph.get_graph().draw_mermaid())

    config = {"configurable":{"thread_id": "frank_test_001"}}

    asyncio.run(
        graph.ainvoke({
            "messages": [HumanMessage(content=query)],
            "original_query": query,
            "current_query": query,
            "retrieval_count": 0,
            "max_retrievals": 3,
            "is_satisfied": False,
            "final_answer": ""
    }, config=config))
