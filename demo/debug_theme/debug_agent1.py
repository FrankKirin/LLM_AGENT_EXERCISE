# 需求：用户问上海天气，Agent应该调用天气工具，然后回答

from typing import Annotated
from typing_extensions import TypedDict

from langchain.messages import HumanMessage, AIMessage, ToolMessage
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages


class State(TypedDict):
    messages: Annotated[list, add_messages]
    city: str
    weather: str


def llm_node(state: State):
    last_message = state["messages"][-1]

    if isinstance(last_message, HumanMessage):
        return {
            "messages": [
                AIMessage(
                    content="",
                    tool_calls=[
                        {
                            "name": "weather",
                            "args": {
                                "city": "上海"
                            },
                            "id": "call_1",
                        }
                    ],
                )
            ]
        }

    if isinstance(last_message, ToolMessage):
        return {
            "messages": [
                AIMessage(
                    content=f"天气是：{last_message.content}"
                )
            ]
        }


def weather_node(state: State):
    print("*"*80)
    print("\n[DEBUG] weather_node state=")
    print(state)
    print("*"*80)
    print("\n")

    city = state["city"]

    print("weather_node 收到 city =", city)

    return {
        "weather": f"{city}今天晴天，25°C",
        "messages": [
            ToolMessage(
                content=f"{city}今天晴天，25°C",
                tool_call_id="call_1",
            )
        ],
    }


def route(state: State):
    last_message = state["messages"][-1]

    if last_message.tool_calls:
        return "weather"

    return END


builder = StateGraph(State)

builder.add_node("llm", llm_node)
builder.add_node("weather", weather_node)

builder.add_edge(START, "llm")

builder.add_conditional_edges(
    "llm",
    route,
)

builder.add_edge("weather", "llm")

graph = builder.compile()

print("&"*50)
print("打印输出graph stream中的event")

for event in graph.stream({
    "messages": [HumanMessage("上海天气怎么样？")],
    "city": "",
    "weather": "",
    },
    stream_mode="updates",
):
    print(event)

# result = graph.invoke({
#     "messages": [
#         HumanMessage("上海天气怎么样？")
#     ],
#     "city": "",
#     "weather": "",
# })

# print(result)
