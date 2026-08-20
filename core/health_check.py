from fastapi import APIRouter
from pydantic import BaseModel
import time
from core.config import settings

router = APIRouter(tags=["健康检查"])
START_TIME = time.time()

class HealthResponse(BaseModel):
    status: str
    service: str
    version: str
    environment: str
    uptime_seconds: float

class ReadinessResponse(BaseModel):
    status: str
    checks: dict[str, str]
    all_healthy: bool

@router.get("/health", summary="存活检查")
async def liveness_check():
    # 进程存活检查，能返回就说明活着
    uptime = time.time() - START_TIME
    return HealthResponse(
        status="healthy",
        service=settings.service_name,
        version=settings.version,
        environment=settings.env.value,
        uptime_seconds=round(uptime, 2)
    )

@router.get("/ready", summary="就绪检查")
async def readiness_check():
    """所有依赖是否就绪，全部通过才能接流量"""
    checks: dict[str, str] = {}
    all_healthy = True

    # 检查base_url
    try:
        _ = settings.llm_base_url
        checks["config"] = "ok"
    except Exception as e:
        checks["config"] = f"error: {e}"
        all_healthy = False

    # 检查内存
    try:
        import psutil
        mem_percent = psutil.virtual_memory().percent
        checks["memory"] = f"ok ({mem_percent}%)" if mem_percent < 90 else f"warning (mem_percent)%"
    except ImportError:
        checks["memory"] = "skipped"

    # 启动时间
    uptime = time.time() - START_TIME
    if uptime >= 10:
        checks["startup"] = "ok"
    else:
        checks["startup"] = f"starting ({uptime:.1f}s)"
        all_healthy = False

    return ReadinessResponse(
        status="ready" if all_healthy else "not_ready",
        checks = checks,
        all_healthy = all_healthy,
    )