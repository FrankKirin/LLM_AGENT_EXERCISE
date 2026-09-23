import os

from langchain_core.tracers.langchain import LangChainTracer

def get_langsmith_tracer() -> LangChainTracer:
    return LangChainTracer(
        project_name=os.getenv(
            "LLM_AGENT_EXERCISE"
        )
    )
