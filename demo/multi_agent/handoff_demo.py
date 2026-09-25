from core.lc_baseline import llm
from langchain.tools import tool
from langgraph.graph import StateGraph, MessagesState, START, END
from langgraph.prebuilt import ToolNode, InjectedState
from langgraph.types import Command

# handoff tool作用是吧控制前交给指定Agent
def create_handoff_tool(agent_name: str, description: str):
    tool_name = f"transfoer_to_{agent_name}"

