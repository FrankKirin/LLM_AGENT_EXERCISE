from core.config import settings
from typing import Annotated, List, TypedDict
import operator
from pydantic import BaseModel, Field
from core.lc_baseline import llm
from langchain.messages import HumanMessage, SystemMessage, ToolMessage
from langgraph.types import Send
from langgraph.graph import StateGraph, END, START
from rich import print


class Section(BaseModel):
    name: str = Field(
        description="Name for this section of the report"
    )
    description: str = Field(
        description="Brief overview of the main topics and concepts to be covered in this section"
    )

# Section List类
class Sections(BaseModel):
    sections: List[Section] = Field(
        description = "Sections of the report."
    )

# 希望模型输出符合Sections的结构
planner = llm.with_structured_output(Sections, method="json_mode")

# Graph State
class State(TypedDict):
    topic: str
    sections: List[Section]
    completed_sections: Annotated[list, operator.add]   # All workers write to this key in paralledl
    final_report: str

class WorkerState(TypedDict):
    section: Section
    completed_sections: Annotated[list, operator.add]

# Nodes
def orchestrator(state: State):
    """Orchestrator that generates a plan for the report
    """
    report_sections = planner.invoke(
        [  
            # JSON格式不能去掉[]，因为sections类中，定义了Sections: [Section]
            SystemMessage(content="""Output ONLY valid JSON. 
            
                        Generate a plan for the report. 
                        
                        JSON格式为
                        {"sections":[{"name":"报告名字", "description":"详细内容"}]}
                        
                        """),
            HumanMessage(content=f"Here is the report topic: {state['topic']}")
        ]
    )

    return {"sections": report_sections.sections}

def llm_call(state: WorkerState):
    """Worker writes a section of the report"""

    section_detail = llm.invoke([
        SystemMessage(content="Write a report section following the provided name and description. Include no preamble for each section."),
        HumanMessage(content=f"Here is the section name: {state['section'].name} and description: {state['section'].description}")
    ]
    )

    return {"completed_sections": [section_detail.content]}

def assign_workers(state: State):
    return [Send("llm_call", {"section": s}) for s in state["sections"]]

def synthesizer(state: State):
    completed_sections = state["completed_sections"]
    completed_report_sections = "\n\n---\n\n".join(completed_sections)

    return {"final_report": completed_report_sections}
# Build workflow
orchestrator_worker_builder = StateGraph(State)

orchestrator_worker_builder.add_node("orchestrator", orchestrator)
orchestrator_worker_builder.add_node("llm_call", llm_call)
orchestrator_worker_builder.add_node("synthesizer", synthesizer)

orchestrator_worker_builder.add_edge(START, "orchestrator")
orchestrator_worker_builder.add_conditional_edges(
    "orchestrator", 
    # assign_workers返回Send对象，如果不用add_conditional_edges，无法动态创建多个并行
    assign_workers, 
    # assign_workers后的这个节点表示所有assign_workers可能会去的结果
    ["llm_call"]
)
orchestrator_worker_builder.add_edge("llm_call", "synthesizer")
orchestrator_worker_builder.add_edge("synthesizer", END)

orchestrator_worker = orchestrator_worker_builder.compile()

# Show the workflow
print(orchestrator_worker.get_graph().draw_mermaid())
print(orchestrator_worker.get_graph().draw_ascii())

# Invoke
state = orchestrator_worker.invoke({"topic": "整理一个langgraph多Agent协作的报告"})

print("-"*50 + "最终生成结果:" + "-"*50)
print(state["final_report"])

# supervisor节点分解任务、按照分解成的N个Section，发送LLM节点扩写，最后节点汇总report