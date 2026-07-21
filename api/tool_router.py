import sys
from pathlib import Path
ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(ROOT_DIR))
import json
from fastapi import APIRouter
from pydantic import BaseModel
from core.logger import logger
from core.llm_client import client
from core.llm_client import llm_chat_with_tools
from core.tools import TOOLS_DEF
from core.tool_executor import execute_tool

# API接口，路径为/tool，分组是”工具查询对话“
router = APIRouter(prefix="/tool", tags=["工具查询对话"])

class ToolChatReq(BaseModel):
    query: str

MOCK_REQUEST = {"query":"查询OD20260701工单状态"}

@router.post("/chat")
async def tool_chat(req: ToolChatReq):
    messages = [{"role":"user", "content":req.query}]
    # 第一轮 判断是否调用工具
    resp = llm_chat_with_tools(messages, TOOLS_DEF)
    msg = resp.choices[0].message
    logger.debug(f"LLM返回的resp.choices[0].message内容：{msg}")

    if msg.tool_calls:
        for tool_call in msg.tool_calls:
            tool_res = execute_tool(tool_call)
            messages.append(msg)
            messages.append({
                "role":"tool",
                "tool_call_id":tool_call.id,
                "content":json.dumps(tool_res, ensure_ascii=False),
                # "name":tool_call.function.name
            })
            logger.debug(f"执行函数后messages的内容为：{messages}")

        final_resp = llm_chat_with_tools(messages=messages, tools=TOOLS_DEF)
        answer = final_resp.choices[0].message.content
        # 追加内容，并让LLM重新回答
        return answer
    else:
        try:
            result = resp.choices[0].message.content
            logger.debug(f"非工具调用分支，输出回答: {result}")
            return result
        except Exception as e:
            logger.warning(f"LLM返回内容报错：{e}") # 留意一下这个logger有没有写错

# 异步函数调试代码
# if __name__ == "__main__":
#     import asyncio
#     test_req = ToolChatReq(**MOCK_REQUEST)
#     result = asyncio.run(tool_chat(test_req))
#     print("调试返回结果：", result)
