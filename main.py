from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from api.chat_router import router as chat_router
import uuid
import structlog
from core.logger import logger

app = FastAPI(title="LLM练习SSE")
# 注册路由，这是重点
app.include_router(chat_router)

# @app.middleware("http")
# async def add_request_id_middleware(request: Request, call_next):
#     request_id = str(uuid.uuid4())
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