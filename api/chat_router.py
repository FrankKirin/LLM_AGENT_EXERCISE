from pydantic import BaseModel
from fastapi import APIRouter, HTTPException
from typing import List, Dict
from fastapi.responses import StreamingResponse
from core.llm_client import llm_stream_chat
from core.logger import logger

# tags会讲这个路由的接口归到“对话接口”分类下
router = APIRouter(prefix="/chat", tags=["对话接口"])

# 会校验前端传的json是否符合format
class ChatRequest(BaseModel):
    messages: List[Dict[str, str]]

def stream_generator(messages):
    # 用请求参数调用流式接口，strem保存respnose
    try:
        stream = llm_stream_chat(messages)
        for chunk in stream:
            # print("chunk结构:", chunk.model_dump())
            if chunk.choices and chunk.choices[0].delta.content:
                content = chunk.choices[0].delta.content
                # SSE标准格式
                yield f"data: {content}\n\n"
                # yield f"data: {content}\n"
            # SSE流结束标志
            yield "data: [DONE]\n\n"
            # yield "data: [DONE]\n"
    except Exception as e:
        # 错误放在error关键词参数中
        logger.error("流式输出异常", error=str(e))
        # 用yield，而不是raise，SSE核心限制：连接建立后，不能再返回新的HTTP响应, 所以不用raise，用yield
        yield f"data: [ERROR]{str(e)}\n\n"


@router.post("/stream")
async def chat_stream(req: ChatRequest):
    try:
        return StreamingResponse(
            stream_generator(req.messages),
            media_type="text/event-stream"
        )
    except Exception as e:
        logger.error("对话接口顶层异常", error=str(e))
        raise HTTPException(status_code=500, detail=f"服务异常：{str(e)}")

