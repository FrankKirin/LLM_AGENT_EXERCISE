import os
from dotenv import load_dotenv
load_dotenv(override=True)  # 刷新后台缓存变量
import json
from langgraph.graph import StateGraph, START, END
from typing import TypedDict, Annotated
from langchain_openai import ChatOpenAI
from langchain.messages import SystemMessage, HumanMessage
from langgraph.graph.message import add_messages
from langchain_core.tools import StructuredTool, tool
# from langchain.agents import create_agent
from core.config import settings # 为什么这句代码没有让langsmith配置生效
# from common_tools.deal_llm_response import clean_json
from langchain_core.tracers.langchain import wait_for_all_tracers
import os
print("LANGSMITH_API_KEY 已配置:", "LANGSMITH_API_KEY" in os.environ)
print("LANGSMITH_TRACING:", os.environ.get("LANGSMITH_TRACING"))
print("LANGSMITH_PROJECT:", os.environ.get("LANGSMITH_PROJECT", "default"))

class AgentState(TypedDict):
    messages: Annotated[list, add_messages]
    next_step: str # 调度节点用来标记下一步派给谁
    analysis_result: str
    user_query: str
    recent_res: str
    reason: str

llm = ChatOpenAI(
    model=settings.llm_model,
    base_url=settings.llm_base_url,
    api_key=settings.llm_api_key,
    temperature=0.3
)

def build_supervisor_node(worker_names: list[str], tenant_tools: list[StructuredTool]):
    llm = ChatOpenAI(
        model=settings.llm_model,
        base_url=settings.llm_base_url,
        api_key=settings.llm_api_key,
        temperature=0
    ).bind_tools(tenant_tools)

    worker_options = "\n".join(f"-{name}" for name in worker_names)
    tool_descriptions = "\n".join(
       f"-{t.name}:{t.description} " for t in tenant_tools) if tenant_tools else "(无可用工具)"

    # 真正被LangGraph调用的节点函数
    async def supervisor_node(state):
        messages = state["messages"]

        system_prompt = f"""
            你是一个Supervisor Agent。
            你的任务是协调多个Worker完成用户请求。

            可用Worker(可分配专项任务):
            {worker_options}

            可用的工具(可直接调用执行):
            {tool_descriptions}

            处理规则：
            1.如果问题可以用工具直接解决，调用对应工具
            2.如果问题需要专项能力，分配给对应Worker节点处理
            3.工具调用严格使用标准Function Calling格式
            4.所有结果最终整合为完整自然语言回答
        """.strip()

        try:
            response = await llm.ainvoke(
                [SystemMessage(content = system_prompt)] + state["messages"]
            )
        except Exception as e:
            raise ValueError("LLM返回报错")

        return {"messages": [response]}
    return supervisor_node

# Mocked Worker
def analysis_worker(state: AgentState):
    prompt = """你是一个资深的分析师，能够通过对用户问题、最新回答、答案不满意的原因进行
    全面，深入的思考，分析用户问题，罗列出撰写报告的提纲

    用户问题：{state['user_query']}
    最新回答：{state['recent_res']}
    答案不满意的原因: {state['reason']}
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
    prompt = """你是一个擅长总结和写报告的助手，能够根据用户问题，分析的提纲和框架，答案不满意的原因，
    给出一份符合分析提纲和框架，紧扣用户问题，思路清晰的报告

    用户问题：{state['user_query']}
    分析提纲和框架: {state['analysis_result']}
    答案不满意的原因：{state['reason']}
"""
    messages = [
        SystemMessage(content=prompt),
        HumanMessage(content=state['user_query'])
    ]
    res = llm.invoke(messages)
    return {
        "recent_res": res.content
    }

# 方法1
def fetch_weather(location:str="Beijing"):
    """
        查询城市天气，用户输入城市
        Args:
            localtion: 城市名称，如Beijing，Shanghai
    """
    info = {"Beijing": "25C", "Shanghai":"30C"}
    if info.get(location, ""):
        return info[location]

def supervisor_node(state:AgentState):

    # 必须是f-string形式
    sys_prompt = f"""你是一个智能调度器，负责根据用户需求决定下一步操作。
    可选项：
        -"analysis": 需要对用户问题进行深度分析(需要提取信息、计算或评估时)
        -"FINISH": 已完全满足用户需求，无需进一步操作
    
        请基于当前对话和已有信息做出决策:
        -如果问题不难，直接给出回答, 返回字段answer，并把答案保存在answer里
        -需要进一步分析或者当前问题答案你觉得不足以准确，清晰回答用户问题，就转去analysis节点，返回字段next_step赋值analysis
        -如果资料足够对问题给出答案，就结束，返回字段next_step赋值FINISH
        用户问题：{state['user_query']}
        当前问题答案：{state['recent_res']}

        基于问题答案内容，给出本次report内容没有达到或者达到预期的理由, 保存到返回的字段reason中

        输出可选项: 'analysis' | 'FINISH'
        必须用JSON格式输出，格式为{{"answer": "这个问题的答案就是这样", "next_step":"analysis", "reason":"本次报告内容缺少理论依据"}}
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
        if next_step not in ("analysis","FINISH"):
            raise ValueError(f"非法next: {next_step}")

        reason = content.get("reason")
        print("="*50)
        answer = content.get("answer")
        print(f"supervisor节点答案：{answer}, 模型给的理由: {reason}")
        return {
            "next_step": next_step,
            "reason": reason,
            "recent_res": answer,
        }

    except Exception as e:
        # 第一层解决：网络错误、API错误、超时、服务端错误
        print(f"捕获到异常，具体内容为：{str(e)}")
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
            "FINISH": END}
        )

    graph.add_edge("analysis_worker", "report_worker")
    graph.add_edge("report_worker", "supervisor")

    comp_graph = graph.compile()
    print(comp_graph.get_graph().draw_mermaid())

    return comp_graph

if __name__ == "__main__":
    graph = build_graph()
    query1 = "你是什么模型?"
    query2 = "给我介绍一下MCP和Skills的概念，以及说明一下这两个是怎么成为Agent标准的?"

    try:
        res = graph.invoke({
            "messages": [],
            "next_step": "",
            "analysis_result": "",
            "user_query": query1,
            "reason":"",
            "recent_res":""
        })

        print(f"最终结果:{res['recent_res']}")
    finally:
        wait_for_all_tracers()