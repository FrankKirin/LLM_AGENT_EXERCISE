"""
灰度发布中间件：
- 请求进来根据user_id决定版本
- 版本信息注入request.state
- 响应头带版本号和trace_id
- 记录版本请求统计
"""
from fastapi import Request
import time
from starlette.middleware.base import BaseHTTPMiddleware
from core.structured_logger import set_request_context, clear_request_context, log_info
from core.version_manager import version_manager

class VersionMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request:Request, call_next):
        user_id = request.headers.get("X-User-ID") or request.query_params.get("user_id", "anonymous")
        version = version_manager.get_version_for_user(user_id)
        trace_id = set_request_context(user_id=user_id)

        start = time.time()
        is_error = False
        try:
            request.state.version = version
            request.state.trace_id = trace_id
            response = await call_next(request)
            response.headers["X-APP-Version"] = version
            response.headers["X-Trace-ID"] = trace_id
            if response.status_code >= 500:
                # 500h会被记录error
                is_error = True
            return response
        except Exception:
            is_error = True
            raise
        finally:
            version_manager.record_request(version, is_error=is_error)
            log_info("请求完成", version=version, path=request.url.path,
                     duration_ms=round((time.time()-start)*1000, 2), error=is_error)
            clear_request_context()