from dotenv import load_dotenv
load_dotenv(override=True)
from core.config import settings

import os
from langchain_openai import ChatOpenAI
from langchain_core.tracers.langchain import wait_for_all_tracers

print("TRACING =", os.getenv("LANGSMITH_TRACING"))
print("PROJECT =", os.getenv("LANGSMITH_PROJECT"))
print("ENDPOINT =", os.getenv("LANGSMITH_ENDPOINT"))

llm = ChatOpenAI(
    model=settings.llm_model,
    base_url=settings.llm_base_url,
    api_key=settings.llm_api_key,
)

try:
    res = llm.invoke("hello")
    print(res.content)
finally:
    wait_for_all_tracers()