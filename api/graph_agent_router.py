from fastapi import APIRouter
from pydantic import BaseModel
from core.react_graph import build_production_agent
from langchain.messages import HumanMessage


router = APIRouter(prefix="/graph-agent", tags=["Langgraph智能体"])

class ChatRequest(BaseModel):
    session_id: str
    query: str

@router.post("/chat")
async def chat_with_agent(req: ChatRequest):
    agent = build_production_agent()
    config = {
        "configurable": {"thread_id": req.session_id},
        "recursion_limit": 8
    }

    result = await agent.ainvoke(
        {"messages":[HumanMessage(content=req.query)]},
        config = config
    )

    return {
        "code": 0,
        "data": {
            "reply": result["messages"][-1].content,
            "step_count": len(result["messages"])
        }
    }