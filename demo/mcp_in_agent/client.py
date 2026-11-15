# client负责调用开发好的mcp server
import anyio
from mcp import Client
from mcp.types import TextContent, TextResourceContents

async def client_main():
    # 1.连接MCP Server
    async with Client("http://127.0.0.1:8000/mcp") as client:
        print("MCP Server信息：")
        print(client.server_info)
        # 2.发现Server提供的工具
        tool_result = await client.list_tools()
        print("\n可用工具：")
        for tool in tool_result.tools:
            print("工具名称: ", tool.name)
            print("工具描述: ", tool.description)
            print("输入Schema: ", tool.input_schema)
            print("-" * 40)

        # 3.调用查询订单工具

        # 4.判断工具是否执行失败

        # 5.读取Resource

        # 6.获取Prompt

if __name__ == "__main__":
    anyio.run(client_main)


# 为什么client是用异步方法，但是server是同步方法实现的