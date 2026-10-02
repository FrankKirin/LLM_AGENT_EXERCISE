from typing import TypedDict
from langgraph.graph import StateGraph, START, END
from langgraph.types import Command

class State(TypedDict):
    user_quer: str
    result: str
    active_agent: str

def supervisor(state: State)->Command:
    query = state["user_query"]

    if "天气" in query:
        return Command(
            update = {"active_agent": "weather"},
            goto = "weather",
        )

    return Command(
        update = {"active_agent": "general"},
        goto="general"
    )

def weather(state: State):
    return {"result": "上海今天25°C"}

def general(state: State):
    return {"resutl": "这是一个普通问题"}

builder = StateGraph(State)

builder.add_node("supervisor", supervisor)
builder.add_node("weather", weather)
builder.add_node("general", general)

builder.add_edge(START, "supervisor")
builder.add_edge("supervisor", "weather")
builder.add_edge("supervisor", "general")

builder.add_edge("weather", END)
builder.add_edge("general", END)

graph = builder.compile()
