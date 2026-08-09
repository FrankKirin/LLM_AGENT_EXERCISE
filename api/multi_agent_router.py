from fastapi import APIRouter
from core.multi_agent import build_multi_agent_graph
from core.human_loop import build_human_loop_graph, human_approve, human_reject
from pydantic import BaseModel
from core.logger import logger
from langchain.messages import HumanMessage

router = APIRouter(prefix="/multi-agent", tags=["多智能体服务"])


class TaskRequest(BaseModel):
    session_id: str
    task: str

@router.post("/task")
async def submit_multi_agent_task(req: TaskRequest):
    """根据用户请求，返回多个agent做好的report
    """
    graph = build_multi_agent_graph()

    result = await graph.ainvoke(
        {
            "messages": [HumanMessage(content=req.task)],
            "original_task": req.task
        }
    )

    return {
        "code": 0,
        "data": {
            "report": result["final_report"],
            "subtask_count": len(result["subtasks"]),
            "worker_count": len(result["worker_results"])
        }
    }

"""
    单元测试
    Graph测试
    API接口测试
    真实LLM测试
"""
