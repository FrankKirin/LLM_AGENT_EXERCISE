from langchain_openai import ChatOpenAI
# from new_tools import tools # 这叫相对路径导入
from core.new_tools import tools   # 绝对路径导入，“LLM_Agent_exercise是你根目录”
from core.config import settings
from core.chat_memory import memory_manager
from langchain.messages import AIMessage, ToolMessage
import json
from core.logger import logger

# 创建LLM并绑定tools
llm = ChatOpenAI(
    base_url = settings.llm_base_url,
    model = settings.llm_model,
    api_key = settings.llm_api_key,
    temperature = 0.1,
    timeout = settings.llm_timeout
).bind_tools(tools)

# 实现ReAct循环 输入用户session_id和用户问题 输出工具调用 拼接会话历史和用户新问题 最多调用3次
# 处理无工具调用场景
# 处理有工具调用场景

async def run_react_agent(session_id: str, user_input: str):
    history = memory_manager.get_history(session_id=session_id).messages
    print("当前历史消息数量：", len(history))

    # messages存了指定session_id的所有历史(AIMessage和HumanMessage)
    messages = [*history, {"role":"user", "content": user_input}]

    max_iter = 3
    iter_count = 0

    # 第一轮： 思考+工具调用
    while iter_count < max_iter:
        iter_count += 1
        # ainvoke会返回一个AIMessage
        ai_msg: AIMessage = await llm.ainvoke(messages)

        logger.debug("AI msg内容", res=ai_msg)

        print(f"第{iter_count} 轮循环 ", ai_msg.tool_calls)

        # 无工具调用，直接回答
        if not ai_msg.tool_calls:
            # 两种不同写法，位置参数和关键字参数
            await memory_manager.add_AIMessage(session_id, user_input)
            await memory_manager.add_HumanMessage(session_id=session_id, content=str(ai_msg.content))
            logger.debug("没有工具调用直接回答的情况", res=ai_msg)
            return ai_msg.content

        # 处理ToolMessage
        tool_res_msgs = []
        for tool_call in ai_msg.tool_calls:
            tool_map = {t.name: t for t in tools}
            # 拿到msg返回的name
            selected_tool = tool_map[tool_call["name"]]
            # 放入参数调用函数
            tool_result = selected_tool.invoke(tool_call["args"])
            # ToolMessage负责把工具执行结果传回模型
            tool_res_msgs.append(ToolMessage(
                content = str(tool_result),
                tool_call_id=tool_call["id"]
            ))

        messages.extend([ai_msg, *tool_res_msgs])

    final_resp = await llm.ainvoke(messages)
    await memory_manager.add_HumanMessage(session_id, user_input)
    await memory_manager.add_AIMessage(session_id, str(final_resp.content))
    logger.debug("存在工具调用", res=final_resp.content)
    return final_resp.content


if __name__ == "__main__":
    import asyncio
    # asyncio.run(run_react_agent("95271", "查询工单OD20260702的信息"))
    asyncio.run(run_react_agent("95271", "查询工号C1002的信息"))
