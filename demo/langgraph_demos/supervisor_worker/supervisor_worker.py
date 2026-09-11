import json
from dotenv import load_dotenv
load_dotenv()
from langgraph.graph import StateGraph, START, END
from typing import TypedDict, Annotated
from langchain_openai import ChatOpenAI
from core.config import settings
from sqlalchemy import select
from core.saas_platform.models.tenant import Tenant
from langchain.messages import SystemMessage, AIMessage, HumanMessage, AnyMessage
from langgraph.graph.message import add_messages
from langgraph.types import Command
from langchain_core.tools import StructuredTool, tool
from core.lc_baseline import llm
from langchain.agents import create_agent
# from core.config import settings # 为什么这句代码没什么作用

class AgentState(TypedDict):
    messages: Annotated[list, add_messages]
    next_step: str # 调度节点用来标记下一步派给谁
    analysis_result: str
    reporter_result: str
    user_query: str
    reason: str

# Mocked Worker
def analysis_worker(state: AgentState):
    prompt = """你是一个资深的分析师，能够通过全面，深入的思考，分析用户问题，综合最新分析结果和最新报告内容，
    给出进一步的分析结果

    用户问题：{state['user_query']}

    最新分析结果: {state['analysis_result']}
    最新报告内容: {state['report_result']}
"""
    messages = [
        SystemMessage(content=prompt),
        HumanMessage(content=state['user_query'])
    ]
    res = llm.invoke(messages)
    return {
        "analysis_result": res.content
    }

def report_worker(state: AgentState):
    prompt = """你是一个擅长总结和写报告的助手，能够根据用户问题，最新分析结果，最新报告内容来完善最终的报告内容,
    输出一份更新的报告内容

    用户问题：{state['user_query']}

    最新分析结果: {state['analysis_result']}
    最新报告内容: {state['reporter_result']}
"""
    messages = [
        SystemMessage(content=prompt),
        HumanMessage(content=state['user_query'])
    ]
    res = llm.invoke(messages)
    return {
        "reporter_result": res.content
    }

def supervisor_node(state:AgentState):
    # 必须是f-string形式
    sys_prompt = f"""你是一个智能调度器，负责根据用户需求决定下一步操作。
    可选项：
        -"analysis": 需要对用户问题进行深度分析(需要提取信息、计算或评估时)
        -"report": 已经拥有分析结果，需要生成最终报告
        -"FINISH": 任务已完全满足用户需求，无需进一步操作
    
        请基于当前对话和已有信息做出决策:
        -需要进一步，分析，就转去analysis节点，返回字段next_step赋值analysis
        -如果只是整理成报告，就转去report节点，返回字段next_step赋值report
        -如果资料足够，就结束，返回字段next_step赋值FINISH
        用户问题：{state['user_query']}
        analysis内容：{state['analysis_result']}
        report内容：{state['reporter_result']}

        基于每次评估的analysis内容和report内容，给出本次report内容没有达到或者达到预期的理由, 保存到返回的字段reason中

        输出可选项: 'analysis' | 'report' | 'FINISH'
        用JSON格式输出，格式为{{"next_step":"analysis", "reason":"本次报告内容缺少理论依据"}}
    """
    messages = [
        SystemMessage(content=sys_prompt),
        HumanMessage(content=state['user_query']),
    ]

    try: # 防止invoke失败
        res = llm.invoke(messages)
        content = res.content
        # 结果格式防御:
        if not isinstance(content, str):
            raise ValueError("LLM返回内容不是字符串")

        content = content.strip()  # 这一步处理llm返回```json```内容的场景，比较常见
        if content.startswith("```"):
            content = content.replace("```json", "")
            content = content.replace("```", "")
            content = content.strip()

        if not content:
            raise ValueError("LLM返回内容为空")  # ValueError表示“类型对，值不对”
        try:
            content = json.loads(content)
        except json.JSONDecodeError:
            raise ValueError(
                f"LLM返回的不是合法JSON:{content}"
            )

        next_step = content.get("next_step")
        if next_step not in ("analysis_worker","report_worker","FINISH"):
            raise ValueError(f"非法next: {next_step}")

        reason = content.get("reason")
        return {
            "next_step": next_step,
            "reason": reason
        }

    except Exception as e:
        # 第一层解决：网络错误、API错误、超时、服务端错误
        print(f"捕获到异常，具体内容为：str(e)")
        return {
            "next_step": "FINISH"
        }

def build_graph():
    graph = StateGraph(AgentState)
    graph.add_node("analysis_worker", analysis_worker)
    graph.add_node("report_worker", report_worker)
    graph.add_node("supervisor", supervisor_node)

    graph.add_edge(START, "supervisor")
    graph.add_conditional_edges(
        "supervisor",
        lambda s: s["next_step"],
        {
            "analysis":"analysis_worker",
            "report":"report_worker",
            "FINISH": END}
        )

    graph.add_edge("analysis_worker", "supervisor")
    graph.add_edge("report_worker", "supervisor")

    comp_graph = graph.compile()
    print(comp_graph.get_graph().draw_mermaid())

    return comp_graph

if __name__ == "__main__":
    graph = build_graph()
    query = "给我一份有关AI Agent的发展报告，不超过500字"
    res = graph.invoke({
        "messages": [query],
        "next_step": "",
        "analysis_result": "",
        "reporter_result": "",
        "user_query": query,
        "reason":""
    })

    print(f"最终结果:{res['reporter_result']}")