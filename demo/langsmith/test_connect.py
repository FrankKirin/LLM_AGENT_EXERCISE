from dotenv import load_dotenv
load_dotenv(override=True)

from langchain_openai import ChatOpenAI
from langchain_core.tracers.langchain import LangChainTracer
from langchain_core.tracers.langchain import wait_for_all_tracers
from core.config import settings

tracer = LangChainTracer(
    project_name="LS_DEBUG_TEST"
)

llm = ChatOpenAI(
    model=settings.llm_model,
    base_url=settings.llm_base_url,
    api_key=settings.llm_api_key,
)

try:
    result = llm.invoke(
        "这是一次 LangSmith 测试",
        config={
            "callbacks": [tracer]
        },
    )

    print(result.content)

finally:
    wait_for_all_tracers()