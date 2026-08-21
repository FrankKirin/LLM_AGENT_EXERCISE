import os
from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from api.chat_router import router as chat_router
from api.tool_router import router as tool_router
from api.rag_router import router as rag_router
from core.logger import logger
from core.llm_client import llm_chat_with_tools
from api.chat_router import router as agent_router
from api.agent_router import router as agent_react_router
from api.multi_agent_router import router as multi_agent_router

app = FastAPI(title="LLM练习SSE")
# 注册路由，这是重点
app.include_router(chat_router)
app.include_router(tool_router)
app.include_router(agent_router)
app.include_router(rag_router)
app.include_router(agent_react_router)
app.include_router(multi_agent_router)
load_dotenv()

# 全局异常处理器
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error("全局未捕获异常", url=str(request.url), error=str(exc))
    return JSONResponse(
        status_code=500,
        content={"code": 500, "msg": f"服务内部错误: {str(exc)}"}
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
