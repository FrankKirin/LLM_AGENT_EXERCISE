"""
业务要求：
    天气问题：->Supervisor直接调用weather
    复杂研究问题：
            ->Supervisor调用Researcher Agent
            ->Researcher自己进行搜索
            ->Researcher把结果返回Supervisor

    购买问题->Supervisor Handoff 给Sales Agent
"""
from typing import TypedDict, Annotated
from langchain.messages import HumanMessage
from langgraph.graph.message import add_messages

class State(TypedDict):
    # Annotated[xxx, reducer]
    messages: Annotated[list, add_messages]
    active_agent: str
    research_result: str

class ResearchState(TypedDict):
    pass