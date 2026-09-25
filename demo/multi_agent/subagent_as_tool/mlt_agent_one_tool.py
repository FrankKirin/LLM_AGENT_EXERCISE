from langchain.tools import tool
from langchain.agents import create_agent
from core.lc_baseline import llm

# Sub-agnets developed by different teams
research_agent = create_agent(
    model=llm,
    system_prompt="你是一个研究专家",
)
writer_agent = create_agent(
    model=llm,
    system_prompt="你是一个写作专家",
)

SUBAGENTS = {
    "research": research_agent,
    "writer": writer_agent,
}

# task的agent_name和desc是由主代理在运行时根据用户请求和系统提示动态决定
# agent_name：SUBAGENTS字典的键，desc是主代理生成的子任务描述
# 动态委派
@tool
def task(agent_name:str, desc: str)->str:
    """
    启动一个用于任务的临时subagent。

    可用agents：
    - research: 研究和调查
    - writer: 内容创建和编辑 
    """
    agent = SUBAGENTS[agent_name]
    result = agent.invoke({
        "messages": [
            {"role":"user", "content": desc}
        ]
    })

    return result["messages"][-1].content

main_agent = create_agent(
    model=llm,
    tools=[task],
    system_prompt=(
        "你有可选的指定子Agent."
        "可选：research(找事实),"
        "writer(内容创作)."
        "使用task tool来完成工作, 最后的输出的内容必须是中文输出, 报告简明扼要，不超过500字"
    ),
)

res = main_agent.invoke({
    "messages": [{"role":"user", "content":"你是什么模型?"}]
})

for m in res["messages"]:
    m.pretty_print()
    print("\n")
    print("-"*50)
    print("\n")
