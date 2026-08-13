"""
记忆管理智能体
why?
    - 手动管理记忆很麻烦：什么时候该生成摘要，哪些信息值得长期记住，记忆太多了怎么清理？记忆冲突了怎么处理

用langgraph构建记忆管理状态图
触发器：会话达到N轮/用户明确说 “记住”、定时任务
工作流：分析对话->提取记忆->去重/更新->存储

核心节点：
1.分析对话内容：analyze_node
2.提取记忆条目：extract_node
3.去重和更新：deduplicate_node
4.保存到长期记忆: save_node
"""
from typing import TypedDict, Annotated
import operator
import json
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage, AnyMessage
from langgraph.graph import START, END, StateGraph
from langgraph.checkpoint.memory import InMemorySaver 
from core.lc_baseline import llm
from core.memory_manager import memory_manager
from core.logger import logger
from langchain_core.documents import Document 

class MemoryAgentState(TypedDict):
    messages: Annotated[list[AnyMessage], operator.add]
    conversation_text: str # 待分析的对话文本
    user_id: str
    existing_memories: list[dict]
    extracted_memories: list[dict]
    final_memories: list[dict]

async def analyze_conversation_node(state: MemoryAgentState):
    """分析对话内容，判断是否有值得记住的信息
    输入：
        state["conversation_text"][:2000]
    处理：
        llm按照prompt输出{"has_new_info":"", types:"", "importance":"", "summary":""}
    输出：
        state中追加一条分析完成的AI Message 
    """
    prompt = f"""
    请分析以下对话，判断是否有值得长期记住的用户信息。

    对话内容：
    {state['conversation_text'][:2000]}

    请回答：
    1.是否有新的值得记住的信息?（是/否）
    2.信息类型：preference/fact/goal/habit/opinion
    3.重要程度：high/medium/low
    4.简要说明有哪些信息

    用JSON格式回答：
    {{"has_new_info": true/false, "types":[], "importance": "low", "summary":""}}
    """
    response = await llm.ainvoke(prompt)
    content = response.content

    if not isinstance(content, str):
        logger.error("提取记忆内容失败：LLM返回的内容不是字符串")
        return []
    try:
        result = json.loads(content)
    except json.JSONDecodeError as e:
        logger.warning("对话分析节点JSON载入错误{str(e)}")
        result = {"has_new_info": False, "types":[], "importance":"low", "summary":"Json load failed"}

    return {"messages": [AIMessage(content=f"分析结果：{result.get('summary'), ''}")]}

async def extract_memories_node(state: MemoryAgentState):
    """从对话中提取记忆条目
    输入:
        用户历史聊天文本state['conversation_text']
    处理：
        文本输出为列表
        [{content, type, importance}, {content, type, importance}, ...]
    输出：
        state["extracted_memories"]更新为llm输出的文本, 格式 [str1, str2, str3]
    """
    prompt = f"""
    请从以下对话中提取值得长期记住的用户信息。

    对话内容：
    {state['conversation_text'][:2000]}

    要求：
    1.每条记忆用一句话清晰描述
    2.标注类型：preference/fact/goal/habit/opinion
    3.标注重要程度：high/medium/low
    4.只提取明确表达的信息，不要推测

    输出JSON数组格式：
    [
        {{"content":"记忆内容", "type": "fact", "importance":"high"}}
    ]
    """
    response = await llm.ainvoke(prompt)
    content = response.content

    if not isinstance(content, str):
        logger.error("记忆提取失败：LLM返回的内容不是字符串")
        memories = []
    else:
        try:
            memories = json.loads(content)
            if not isinstance(memories, list):
                memories = []
        except json.JSONDecodeError as e:
            logger.error("记忆提取JSON解析失败", error=str(e))
            memorie = []

    logger.debug("extract memories node内容", memories=memories)

    return {
        "extracted_memories": memories,
        "messages": [AIMessage(content=f"提取到{len(memories)}条记忆")]
    }

def deduplicate_memories_node(state: MemoryAgentState):
    """
    输入：
        新的提取到的memory: state["extracted_memories"], 作为query
    处理：
        通过记忆管理器根据输入检索到top5的向量
        通过比对每个新的content[:20]是否被老的content包含或者老的content[:20]是否被新的content包含
        只要不满足条件就追加，满足条件就跳过
    输出：
        新的state["final_memories"]:[str1, str2, str3...]
    """
    # new_memories: list[dict]
    new_memories = state["extracted_memories"]
    if not new_memories:
        return {"final_memories":[]}

    # 用新的长期记忆内容，来检索已有记忆
    query = " ".join([m.get("content", "") for m in new_memories[:3]])
    existing = memory_manager.retrieve_relevant_memories(query, top_k=5)
    # existing_mem: list[str]
    existing_mem = existing["long_term"]

    # 去重逻辑：对比新记忆和老记忆content前20字符是否互相包含来判断
    final_memories = []
    for new_mem in new_memories:
        new_content = new_mem.get("content", "")
        is_duplicate = False

        for old_mem in existing_mem:
            if new_content[:20] in old_mem or old_mem[:20] in new_content:
                is_duplicate = True
                break

        if not is_duplicate:
            final_memories.append(new_mem)

    return {
        "existing_memories":[{"content": c} for c in existing_mem],
        "final_memories": final_memories
    }

def save_memories_node(state: MemoryAgentState):
    """保存记忆到长期存储"""
    memories = state["final_memories"]
    if not memories:
        # return AIMessage可以充当Message里的轨迹记录
        return {"messages": [AIMessage(content="无新记忆需要保存")]}

    # 转为Document，存入向量数据库
    document = [
        Document(
            page_content=mem.get("content", ""),
            metadata={
                "user_id": state["user_id"],
                "importtance": mem.get("importance", "medium"),
                "memory_type": "long_term_memory",
            }
        )
        for mem in memories
    ]
    memory_manager.long_term.add_documents(document)

    return {
        "messages": [AIMessage(content="新的长期记忆保存成功")]
    }


def route_after_extract(state: MemoryAgentState):
    if state["extracted_memories"]:
        return "deduplicate"
    return END

def route_after_deduplicate(state: MemoryAgentState):
    if state["final_memories"]:
        return "save"
    return END


def build_memory_agent_graph():
    workflow = StateGraph(MemoryAgentState)

    workflow.add_node("analyze", analyze_conversation_node)
    workflow.add_node("extract", extract_memories_node)
    workflow.add_node("deduplicate", deduplicate_memories_node)
    workflow.add_node("save", save_memories_node)

    workflow.add_edge(START, "analyze")
    workflow.add_edge("analyze", "extract")

    workflow.add_conditional_edges(
        "extract",
        route_after_extract,
        ["deduplicate", END]
    )

    workflow.add_conditional_edges(
        "deduplicate",
        route_after_deduplicate,
        ["save", END]
    )

    check_pointer = InMemorySaver()

    # 等价于 return workflow.compile(checkpointer = check_pointer)
    compiled_graph = workflow.compile(checkpointer=check_pointer)
    return compiled_graph

