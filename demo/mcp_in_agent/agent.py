import os
import json
import anyio

from dotenv import load_dotenv

from mcp import Client
from mcp.types import CallToolResult, TextContent

from langchain_openai import ChatOpenAI
from langchain_core.messages import (
    SystemMessage,
    HumanMessage,
    ToolMessage,
)

# 1.将MCP工具执行结果转换成文本
def mcp_result_to_text(result: CallToolResult) -> str:
    """
    输入: result
    输出: 
    """
    # 获取mcp返回结果的所有content或者TextContent构成的列表
    # 处理结果有错误的情况，处理result返回为None的情况
    text_parts = [
        content.text
        for content in result.content
        if isinstance(content, TextContent)
    ]
    if result.is_error:
        return "MCP工具执行失败:" + "\n".join(text_parts)

    # 如果结构化内容非None, 直接利用json处理结构化数据，否则自己用“\n”拼接数据
    if result.structured_content is not None:
        return json.dumps(
            result.structured_content,
            ensure_ascii=False,
        )
    return "\n".join(text_parts)

# 2.Agent主流程
async def agent_main():
    """
    1.创建llm
    2.获取MCP的tool
    3.将MCP的tool转换成模型tool格式
    4.llm绑定模型tool 
    """
    load_dotenv()
    llm_base_url = os.getenv("LLM_BASE_URL")
    llm_model = os.getenv("LLM_MODEL")
    llm_api_key = os.getenv("LLM_API_KEY")

    if not all([llm_api_key, llm_model, llm_base_url]):
        raise ValueError("LLM配置不完整，请检查.env")

    llm = ChatOpenAI(
        base_url=llm_base_url,
        model=llm_model,
        api_key=llm_api_key,
    )

    async with Client("http://127.0.0.1:8000/mcp") as client:
        tool_list = await client.list_tools()

        # 工具Schema转换成模型工具
        # type和function字典中的key都是

        # OpenAI Chat Completions API对tools参数的规定，不能乱改
        # 这部分转换是核心
        model_tools = [{
            "type": "function",
            "function": {
                "name": tool.name,
                "description": tool.description or "",
                "parameters": tool.input_schema,
            },
        } for tool in tool_list.tools]

        llm_with_tools = llm.bind_tools(model_tools)

        messages = [
            SystemMessage(
                content=(
                    "你是企业订单助手。"
                    "需要查询订单时，优先调用订单查询工具。"
                    "不要编造订单信息。"
                )
            ),
            HumanMessage(content="请查询订单ORD-1001的物流状态")
        ]

        for _ in range(5):
            ai_message = llm_with_tools.invoke(messages)
            messages.append(ai_message)

            if not ai_message.tool_calls:
                print("\nAgent最终回答：")
                print(ai_message.content)

                return

            for tool_call in ai_message.tool_calls:
                tool_name = tool_call["name"]
                tool_args = tool_call["args"]
                tool_call_id = tool_call["id"]

                print("\n模型请求调用工具：", tool_name)
                print("工具参数：", tool_args)
                # 通过MCP Client执行tool
                result = await client.call_tool(
                    tool_name,
                    tool_args,
                )
                tool_message = ToolMessage(
                    content=mcp_result_to_text(result),
                    tool_call_id=tool_call_id,
                )
                messages.append(tool_message)
        print("已经达到最大工具调用轮数，终止本次执行。")

if __name__ == "__main__":
    anyio.run(agent_main)
