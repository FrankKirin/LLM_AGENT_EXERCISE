"""
Prometheus指标收集模块
1.定义业务相关监控指标
2.中间件自动请求指标，零侵入
3.暴露/metrics端点供Prometheus抓取
"""
from prometheus_client import(
    Counter, Gauge, Histogram, generate_latest, CONTENT_TYPE_LATEST
)
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
import time

# Counter是只增不减的计数
REQUEST_COUNT = Counter(
    "agent_requests_total", "请求总数",     # 指标名称和指标说明
    ["endpoint", "method", "status_code"]   # 标签Label
)

# Histogram统计耗时分布
REQUEST_LATENCY = Histogram(
    "agent_request_duration_seconds", "请求延迟(秒)",
    ["endpoint"],
    buckets=(0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0)
)

# Gauge计数可以增加也可以减少
CONCURRENT_REQUESTS = Gauge(
    "agent_concurrent_requests", "当前并发请求数"
)

LLM_CALL_COUNT = Counter(
    "agent_llm_calls_total", "LLM调用总数",
    ["model", "status"]
)

LLM_TOKEN_USAGE = Counter(
    "agent_llm_tokens_total", "LLM Token消耗",
    ["model", "token_type"]
)

LLM_LATENCY = Histogram(
    "agent_llm_duration_seconds", "LLM调用延迟(秒)",
    ["model"]
    buckets=(0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0)
)

AGENT_ITERATION_COUNT = Histogram(
    "agent_iterations", "Agent迭代轮次",
    ["agent_type"],
    buckets = (1,2,3,5,8,10)
)

TOOL_CALL_COUNT = Counter(
    "agent_tool_calls_total", "工具调用总数",
    ["tool_name", "status"]
)

ERROR_COUNT = Counter(
    "agent_errors_total", "错误总数",
    ["error_type", "endpoint"]
)

# 监控中间件, 拦截每一个FastAPI请求
class MetricsMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # 排除以下几个路径
        if request.url.path in ["/metrics", "/health", "/ready"]:
            return await call_next(request)

        endpoint = request.url.path
        method = request.method
        CONCURRENT_REQUESTS.inc()   # 并发数+1
        start_time = time.time()

        try:
            response = await call_next(request)     # 真正执行接口
            status_code = response.status_code
            
            REQUEST_COUNT.labels(
                endpoint = endpoint, method = method, status_code = status_code
            ).inc() # 记录请求次数

            if status_code >= 500:
                ERROR_COUNT.labels(error_type="http_5xx", endpoint=endpoint).inc()
            return response
        except Exception as e:
            ERROR_COUNT.labels(error_type=type(e).__name__, endpoint=endpoint).inc()
            raise
        finally:
            duration = time.time() - start_time
            REQUEST_LATENCY.labels(endpoint=endpoint).observe(duration)
            CONCURRENT_REQUESTS.dec()

def get_metrics_response() -> Response:
    """把Python程序中的Prometheus指标转换成HTTP响应
       generate_latest()获取当前所有Prometheus指标 
    """
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)

# 以下函数都是手动埋点
# LLM, Took, Agent指标中间件无法看到具体细节
def record_llm_call(model: str, duration: float, status: str="success",
                    prompt_tokens: int=0, completion_tokens: int=0):
    LLM_CALL_COUNT.labels(model=model, status=status).inc()
    LLM_LATENCY.labels(model=model).observe(duration)
    if prompt_tokens:
        LLM_TOKEN_USAGE.labels(model=model, token_type="prompt").inc(prompt_tokens)
    if completion_tokens:
        LLM_TOKEN_USAGE.labels(model=model, token_type="completion").inc(completion_tokens)

def record_tool_call(tool_name: str, status: str="success"):
    TOOL_CALL_COUNT.labels(tool_name=tool_name, status=status).inc()

def record_agent_iteration(agent_type: str, iterations: int):
    AGENT_ITERATION_COUNT.labels(agent_type=agent_type).observe(iterations)