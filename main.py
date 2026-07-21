from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from api.chat_router import router as chat_router
from api.tool_router import router as tool_router
from core.logger import logger
from core.llm_client import llm_chat_with_tools

app = FastAPI(title="LLM练习SSE")
# 注册路由，这是重点
app.include_router(chat_router)
app.include_router(tool_router)

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

# main函数中创建fastapi应用，注册chat_router这个路由，额外定义全局异常处理来捕获没写的异常
# 