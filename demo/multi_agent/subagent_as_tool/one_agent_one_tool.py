# One SubAgent one tool
from langchain.agents import create_agent
from langchain.tools import tool
from core.config import settings
from core.lc_baseline import llm

# 创建有自主能力的agent
research_agent = create_agent(
    model = llm,
    tools = [],
    system_prompt="你是研究专家，负责查找和分析资料。",
)

report_agent = create_agent(
    model = llm,
    tools = [],
    system_prompt="你是写报告的专家，负责将手头所有内容整理成逻辑通顺，结构清晰的报告"
)

@tool
def research(request: str)->str:
    """让研究Agent处理需要资料检索和分析的问题"""
    result = report_agent.invoke({
        "messages":[{"role":"user", "content": request}]
    })
    return result["messages"][-1].content

@tool
def report(request: str)->str:
    """让报告Agent根据已有信息生成最终的报告"""
    result = report_agent.invoke({
        "messages":[{"role":"user", "content": request}]
    })
    return result["messages"][-1].content

supervisor = create_agent(
    model = llm,
    tools=[research, report],
    system_prompt="""
    你是总协调Agent。
    根据用户问题选择合适的专项Agent。
    如果一个问题需要多个专项Agent，可以依次调用。
    综合结果后给用户最终回答, 回答简明扼要，控制在500字以内
    """
)

# 常规输出，等llm全部执行结束后输出
result = supervisor.invoke({
    # No.1 human_message
    "messages": [
        {"role":"user", "content": "帮我研究一下临港新片区的将来发展前景，并整理成报告"}
    ]
})

# 自带工具版本
for m in result["messages"]:
    m.pretty_print()  # Langchain消息自带的格式化打印。

# # 手搓控制格式版本
# def print_trace(messages):
#     for i, m in enumerate(messages):
#         name = getattr(m, "name", None) or m.__class__.__name__.replace("Message", "")
#         tc = getattr(m, "tool_calls", None)
#         content = m.content if isinstance(m.content, str) else str(m.content)[:100]
#         print(f"[{i}] {name}: {content}")
#         if tc:
#             for c in tc:
#                 print(f"    → 调用工具 {c['name']}，参数: {c['args']}")

# print_trace(result["messages"])