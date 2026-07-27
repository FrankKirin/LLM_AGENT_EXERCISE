from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from core.react_agent_new import run_react_agent

# 创建router，定义好prefix
router = APIRouter(prefix="agent", tags="ReAct智能体")

class AgentChatReq(BaseModel):
    session_id: str
    query: str

@router.post("/chat")
async def agent_chat(req: AgentChatReq):
    try:
        reply = await run_react_agent(req.session_id, req.query)
        return {
            "code": 0,
            "data": {"reply":reply}
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"智能体执行异常：{str(e)}")

