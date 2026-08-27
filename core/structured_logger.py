"""
结构化日志：
 - JSON格式，直接导入ELK/Loki分析
 - 每个请求唯一trace_id，贯穿调用链
 - 按字段过滤: trace_id、user_id、error_type
 告警体系：
 - P0:立即、P1:1小时、P2:工作日
 - 冷却时间防告警风暴
 - 告警必须可操作
"""
import time
import asyncio
import functools
import uuid
import traceback
import inspect
from structlog import get_logger
from typing import Optional
from core.config import settings
from contextvars import ContextVar  # 用来跟踪异步上下文

# 定义trace_id、user_id、session_id
# 类型参数，ContextVar中的值可以是str，也可以是None
trace_id_var: ContextVar[Optional[str]] = ContextVar("trace_id", default=None)
user_id_var: ContextVar[Optional[str]] = ContextVar("user_id", default=None)
session_id_var: ContextVar[Optional[str]] = ContextVar("session_id", default=None)
logger = get_logger()

def generate_trace_id() -> str:
    # 生成一个长度为36的uuid, uuid4最常用: 完全随机并且不会暴露mac地址
    return str(uuid.uuid4())

def get_trace_id() -> Optional[str]:
    return trace_id_var.get()

def clear_request_context():
    # 上下文总共就trace_id, user_id和seesion_id三个
    trace_id_var.set(None)
    user_id_var.set(None)
    session_id_var.set(None)

def set_request_context(trace_id: str = None, user_id: str= None, session_id: str = None) -> str:
    if user_id:
        user_id_var.set(user_id)
    if session_id:
        session_id_var.set(session_id)
    if trace_id is None:
        trace_id = generate_trace_id()
    trace_id_var.set(trace_id)
    return trace_id

def log_with_context(log_level: str, event: str, **kwargs):
    """
    输入：
        context捕获固定指定字段
        **kwargs获取传进来的字段
    处理：
        过滤掉context中value为None的上下文
        根据event使用logger.info/error/warning, 如果获取不到就用logger.info()函数
        log_func是logger.info/error/warning函数的变量名
    输出：

    """
    context = {
        "trace_id": trace_id_var.get(),
        "user_id": user_id_var.get(),
        "session_id": session_id_var.get(),
        "app_version": settings.version,
        "service": settings.service_name,
        "environment": settings.env.value,
    }
    context = {k:v for k, v in context.items() if v is not None}
    # getattr语法：getattr(object, name, default)
    # 获取logger对象的level属性，如果没有值就获取logger.info
    log_func = getattr(logger, log_level, logger.info)
    # python中函数也是变量
    log_func(event, **context, **kwargs)

# 定义info, warning, error
def log_info(event: str, **kwargs):
    log_with_context("info", event, **kwargs)

def log_warning(event: str, **kwargs):
    log_with_context("warning", event, **kwargs)

def log_error(event: str, error: Exception = None, **kwargs):
    if error:
        kwargs["error_type"] = type(error).__name__
        kwargs["error_message"] = str(error)
        kwargs["stack_trace"] = traceback.format_exc()
    log_with_context("error", event, **kwargs)

def log_duration(event_name: str):
    """
    输入：
        event_name：事件名
    处理：
        函数装饰器，针对异步函数和同步函数
        用户传的，位置参数作为*args，关键词参数作为kwargs
    输出：
    
    """
    def decorator(func):  
        # 虽然包裹的是异步函数，但是这个动作本身不需要等IO，所以定义成普通函数
        @functools.wraps(func)
        # 让包装函数wrapper尽可能保留原函数func的身份信息
        async def async_wrapper(*args, **kwargs):
            start = time.time()
            try:
                result = await func(*args, **kwargs)
                log_info(f"{event_name}_完成", duration_ms=round((time.time()-start)*1000, 2))
                return result
            except Exception as e:
                log_info(f"{event_name}_失败", error=e, duration_ms=round((time.time()-start)*1000, 2))
                raise

        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            start = time.time()
            try:
                result = func(*args, **kwargs)
                log_info(f"{event_name}_完成, duration_ms=round((time.time()-start)*1000, 2)")
                return result
            except Exception as e:
                log_info(f"{event_name}_失败, error=e, duration_ms=round((time.time()-start)*1000, 2)")
                raise
        # 自动识别同步、异步
        return async_wrapper if inspect.iscoroutinefunction(func) else sync_wrapper
    return decorator