# 这一层用来创建SSE流式请求客户端
# 实现流式请求业务逻辑
# 核心：LLM调用 + 指数退避重试
from openai import OpenAI, APIError, APITimeoutError
from core.config import settings
from core.logger import logger
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

client = OpenAI(
    base_url = settings.LLM_BASE_URL,
    api_key = settings.LLM_API_KEY,
    timeout = settings.LLM_TIMEOUT
)

@retry(
    stop=stop_after_attempt(settings.MAX_RETRY_TIMES),
    wait=wait_exponential(multiplier=1, min=1, max=5),
    retry=retry_if_exception_type((APITimeoutError, APIError)),
    # 对于装饰器里的函数，使用lambda表达式可以一眼看到函数的逻辑, 且这个逻辑没有复用价值
    before_sleep=lambda retry_state: logger.warning(
        f"LLM调用失败，准备重试 {retry_state.attempt_number}"
    )
)

def llm_stream_chat(messages: list):
    logger.info("发起LLM流式请求", messages=messages)
    stream = client.chat.completions.create(
        model = settings.LLM_MODEL,
        messages = messages,
        stream=True,
        stream_options={"include_usage": True}
    )
    return stream
