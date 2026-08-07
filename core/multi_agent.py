from core.config import settings
import operator
from langgraph.checkpoint.memory import MemorySaver
from typing import TypedDict, Annotated
from langchain.messages import AnyMessage, AIMessage, HumanMessage, SystemMessage
from core.logger import logger
from langgraph.graph import StateGraph, END, START
from langgraph.checkpoint.memory import MemorySaver
from core.lc_baseline import llm
import json
from rich import print

class MultiAgentState(TypedDict):
    messages: Annotated[list[AnyMessage], operator.add]
    original_task: str
    subtasks: list[dict[str, str]]
    # worker_results不用reducer: Dict合并逻辑复杂，显式手动合并更易调试、更安全
    worker_results: dict[str, str]
    current_worker: str
    final_report: str

# ========== 2. Worker角色定义 ==========
WORKERS = {
    "research_worker": {
        "name": "调研专员",
        "system_prompt": """
        你是专业调研专员，擅长信息收集与事实核查。
        根据任务要求，输出结构化的调研结果。
        只负责信息收集，不做分析结论。
        """.strip()
    },
    "analysis_worker": {
        "name": "分析师",
        "system_prompt": """
        你是资深分析师，擅长数据分析与逻辑推理。
        根据提供的信息进行深度分析，输出结构化分析结论。
        只做分析，不做最终建议。
        """.strip()
    },
    "report_worker": {
        "name": "报告撰写人",
        "system_prompt": """
        你是专业报告撰写人，擅长整合信息撰写专业报告。
        根据调研结果和分析结论，撰写完整最终报告。
        要求结构清晰、逻辑严谨。
        """.strip()
    }
}

# Supervisor节点
# 主管智能体理解用户任务，拆解为多个子任务，分配给对应Worker
async def supervisor_decompose_node(state: MultiAgentState):
    worker_list = "\n".join(
        [f"- {k}: {v['name']} - {v['system_prompt'][:100]}" for k, v in WORKERS.items()]
    )
    prompt = f"""
    你是项目主管, 请将以下任务拆解为子任务，并分配给合适的执行人员。

    可用执行人员
    {worker_list}

    原始任务：{state['original_task']}

    请严格按照JSON格式输出，不要额外文字：
    {{
        "subtasks": [
            {{
                "task_id": "1",
                "description": "子任务描述",
                "assigned_worker": "research_worker",
            }}
        ]
    }}
"""

    response = await llm.ainvoke(prompt)
    print(f"任务拆解完成, content={response.content}")

    try:
        result = json.loads(response.content)
        print(f"supervisor节点中result内容：{result}")
        subtasks = result.get("subtasks", [])
    except Exception as e:
        logger.error("任务拆解解析失败", error=str(e))
        subtasks = [
            {"task_id": "1", "description": state["original_task"],
            "assigned_worker": "research_worker"}
        ]

    return {
        "subtasks": subtasks,
        # subtasks中第一个任务的worker给到current_worker，否则就分配report_worker，report_worker进行兜底
        "current_worker": subtasks[0]["assigned_worker"] if subtasks else "report_worker",
        "worker_results": {},
        "messages": [AIMessage(content=f"已拆解为{len(subtasks)}个子任务")]
    }

# worker_result:手动读取旧状态并合并新结果，避免Dict被整体覆盖
# current_worker:执行完后自动计算并设置下一个worker

async def worker_execute_node(state: MultiAgentState):
    worker_key = state["current_worker"]
    worker_config = WORKERS[worker_key]

    # 找到当前worker对应的子任务
    # next()用于获取迭代器第一个元素，找不到则返回None，不会抛出StopIteration异常
    current_subtask = next(
        (st for st in state["subtasks"] if st["assigned_worker"] == worker_key), {"description": state["original_task"]}
    )
    print(f"work_excute节点中current_subtask内容{current_subtask}")

    # 构建worker的上下文, SystemMessage用来向LLM传递背景规则，角色设定或输出格式要求
    # 已有信息参考使用json.dumps为了对齐排版，提高模型理解力，ensure_ascii=False为了防中文变成乱码
    messages = [
        SystemMessage(content=worker_config["system_prompt"]),
        # 已有的worker_result作为参考信息
        HumanMessage(content=f"""
        请完成以下任务：
        任务描述：{current_subtask['description']}

        已有的参考信息：
        {json.dumps(state['worker_results'], ensure_ascii=False, indent=2)}
""")
    ]

    response = await llm.ainvoke(messages)
    print(f"worker节点的worker_key为{worker_key}")

    worker_results = state["worker_results"]
    worker_results[worker_key] = response.content

    # 计算下一个worker
    all_assigned_worker = [st["assigned_worker"] for st in state["subtasks"]]
    print(f"所有的worker{all_assigned_worker}")
    completed_worker = set(worker_results.keys())
    print(f"已经完成的worker{completed_worker}")
    pending = [w for w in all_assigned_worker if w not in completed_worker]
    print(f"剩下未执行过的worker{pending}")
    new_worker = pending[0] if pending else ""

    return {
        "worker_results": worker_results,
        "current_worker": new_worker,
        "messages": [AIMessage(content=f"{worker_config['name']}完成任务")]
    }


def route_after_worker(state: MultiAgentState):
    if state["current_worker"] == "" or state["current_worker"] is None:
        return "report_aggregate"
    else: 
        return "worker_execute"


async def report_aggregate_node(state: MultiAgentState):
    results_text = "\n\n".join([
        f"【{WORKERS[k]['name']}输出】\n{v}"
        for k,v in state["worker_results"].items()
    ])

    prompt = f"""
    请根据以下各专业人员的工作成果，整合生成一份完整的最终报告。

    原始任务：{state['original_task']}

    各环节输出:
    {results_text}

    要求：
    1. 结构清晰，分章节呈现
    2. 逻辑连贯, 整合各部分内容
    3. 语言专业，适合正式场合
"""

    response = await llm.ainvoke(prompt)

    return {
        "final_report": response.content,
        "messages": [AIMessage(content=response.content)]
    }

def build_multi_agent_graph():
    workflow = StateGraph(MultiAgentState)

    workflow.add_node("supervisor_decompose", supervisor_decompose_node)
    workflow.add_node("worker_execute", worker_execute_node)
    workflow.add_node("report_aggregate", report_aggregate_node)

    
    workflow.add_edge(START, "supervisor_decompose")
    workflow.add_edge("supervisor_decompose", "worker_execute")


    workflow.add_conditional_edges(
        "worker_execute",
        # route_after_worker,
        route_after_worker,
        # 返回哪个字符串就走哪个节点
        {
            "worker_execute": "worker_execute",
            "report_aggregate": "report_aggregate"
        }
    )

    workflow.add_edge("report_aggregate", END)

    # checkpointer = MemorySaver()
    # graph = workflow.compile(checkpointer=checkpointer)
    graph = workflow.compile()


    print("*"*50 + "agent graph架构图" + "*"*50)
    print(graph.get_graph().draw_mermaid())

    return graph

if __name__ == "__main__":
    agent = build_multi_agent_graph()
    # 不配置config，那么memorysaver就不知道存哪里
    config = {"configurable": {"thread_id":"user_004"}}
    import asyncio
    res = asyncio.run(agent.ainvoke(
        {"messages": [HumanMessage(content="分析并总结临港新片区十五五规划经济指标")],
         "original_task":"分析并总结临港新片区十五五规划经济指标"}
    ,config=config))
    print(f"Agent返回的结果{res}")