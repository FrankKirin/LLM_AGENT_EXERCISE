"""
1.智能问答接口
2.记忆查询接口
3.记忆管理接口
4.会话摘要接口

接口设计原则：
- RESTful风格
- 统一返回格式
- 明确的参数校验
- 完善的错误处理
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from core.memory_manager import memory_manager
from core.agentic_rag import build_agentic_rag_graph
from langchain.messages import HumanMessage, AIMessage


router = APIRouter(prefix="/agentic-rag", tags=["Agentic RAG服务"])

class ChatReqeust(BaseModel):
    user_id: str = "default_user"
    session_id: str
    query: str
    max_retrievals: int=3

class MemoryRequest(BaseModel):
    session_id: str
    query: str
    top_k: int = 3

@router.post("/chat")
async def agentic_rag_chat(req: ChatReqeust):

    memory_context = memory_manager.build_memory_context(req.query)

    enhanced_query = f"""
    [用户背景记忆]
    {memory_context}

    [用户当前问题]
    {req.query}

    请结合用户背景和问题，进行检索和问答
    """
    # 构建Agentic Rag
    graph = build_agentic_rag_graph()
    config = {"configurable": {"thread_id": f"{req.user_id}_{req.session_id}"}}

    try:
        result = await graph.ainvoke({
            "messages": [HumanMessage(content=enhanced_query)],
            "original_query": req.query,
            "current_query":"",
            "retrieval_count": 0,
            "max_retrievals": req.max_retrievals,
            "is_satisfied": False,
            "final_answer": ""
        },
        config=config
        )

        memory_manager.add_to_short_term(req.session_id, HumanMessage(content=req.query))
        memory_manager.add_to_short_term(req.session_id, AIMessage(content=result["final_answer"]))

        return {
            "code": 0,
            "data": {
                "answer": result["final_answer"],
                "retrieval_count": result["retrieval_count"],
                "is_satisfied": result["is_satisfied"],
                "memory_context": memory_context
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/memory/query")
def fetch_memory(req: MemoryRequest):

    try:
        context = memory_manager.build_memory_context(req.query)
        memory = memory_manager.retrieve_relevant_memories(req.query, req.top_k)

        return {
            "code": "0",
            "data": {
                "memory_context": context,
                "long_term_memory": memory["long_term"],
                "medium_term_memory": memory["medium_term"],
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/momory/summary")
async def fetch_summary(req: MemoryRequest):

    try:
        summary = await memory_manager.generate_session_summary(req.session_id)

        return {
            "code": 0,
            "data": {
                "summary": summary,
                "session_id": req.session_id
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

