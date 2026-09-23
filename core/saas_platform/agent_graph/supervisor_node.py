from dotenv import load_dotenv
load_dotenv(override=True)  # 刷新后台缓存变量
from langchain_openai import ChatOpenAI
from langchain.messages import SystemMessage
from langchain_core.tools import StructuredTool
from core.config import settings # 为什么这句代码没有让langsmith配置生效
from langchain.messages import HumanMessage

# 返回一个supervisor节点
def build_supervisor_node(worker_names: list[str], tenant_tools: list[StructuredTool]):
    llm = ChatOpenAI(
        model=settings.llm_model,
        base_url=settings.llm_base_url,
        api_key=settings.llm_api_key,
        temperature=0.3
    ).bind_tools(tenant_tools) # bind_tool只是让LLM知道有哪些tools

    worker_options = "\n".join(f"-{name}" for name in worker_names)
    tool_descriptions = "\n".join(
       f"-{t.name}:{t.description} " for t in tenant_tools) if tenant_tools else "(无可用工具)"

    # 真正被LangGraph调用的节点函数
    async def supervisor_node(state):
        system_prompt = f"""
            你是一个Supervisor Agent。

            可用Worker(可分配专项任务):
            {worker_options}

            可用的工具(可直接调用执行):
            {tool_descriptions}

            处理规则：
            1.如果问题可以用工具直接解决，调用对应工具
            2.如果问题需要专项能力，调用对应的transfer_to_*工具
            3.工具调用必须严格按照工具定义执行
            4.所有结果最终整合为完整自然语言回答
            5.如果没有足够的数据或者材料，直接输出'当前可用数据不足，无法做出判断'
        """.strip()

        for i, m in enumerate(state["messages"]):
            print(i, type(m).__name__, type(m.content).__name__, repr(m.content)[:120])

        worker_result = state.get("worker_result")
        if worker_result:
            messages = [
                *state["messages"],
                HumanMessage(content=f"""
        这是专项worker返回的结果：
        worker_name: {worker_result["worker_name"]}

        result:
        {worker_result["data"]}

        请给予这个结果直接回答用户。
        不要再次调用Worker
                """),
            ]

            response = await llm.ainvoke(messages)
        else:
            try:
                response = await llm.ainvoke(
                    [
                        SystemMessage(content = system_prompt), 
                        *state["messages"],
                    ]
                )
            except Exception as e:
                print(f"LLM调用失败的真实原因: {type(e).__name__}: {e}")
                import traceback; traceback.print_exc()
                raise ValueError("LLM返回报错") from e

        return {"messages": [response]}
    return supervisor_node

