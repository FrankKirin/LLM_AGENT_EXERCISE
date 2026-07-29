from fastapi import APIRouter
from pydantic import BaseModel
from core.rag_chain import rag_chain, chat_rag_chain
from core.chat_memory import memory_manager

# 创建router，打上tags
router = APIRouter(prefix="/rag", tags=["RAG知识库"])

# 定义类，继承BaseModel
class RagReq(BaseModel):
    session_id: str
    query: str

# @语法糖定义请求路径，异步调用完成rag聊天
@router.post("/chat")
async def rag_chat(req: RagReq):
    answer = await rag_chain.ainvoke(req.query)
    await memory_manager.add_HumanMessage(req.session_id, answer)
    await memory_manager.add_AIMessage(req.session_id, answer)
    return {"code":0, "data":{"reply": answer}}
