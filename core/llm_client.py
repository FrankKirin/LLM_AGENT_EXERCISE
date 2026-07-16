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
    before_sleep=lambda retry_state: logger.warning(
        f"LLM调用失败，准备重试 {retry_state.attempt_number}"
    )
)

def llm_stream_chat(messages: list):
    logger.info("发起LLM流式请求", messages=messages)
    stream = client.chat.completions.create(
        model = settings.LLM_MODEL,
        messages = messages,
        stream=True
    )
    return stream

# 需要加入失败重试以及log日志