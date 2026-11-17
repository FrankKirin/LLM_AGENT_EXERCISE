# client负责调用开发好的mcp server
import anyio  # 写异步代码的可读性更高，抽象层更高
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

        # 3.调用查询订单工具(重点理解)
        # 返回三个属性：
        #   content: 内容块列表，供模型理解
        #   structured_content: 结构化JSON结果，供程序处理
        #   is_error: 判断工具是否返回执行错误
        res = await client.call_tool( 
            "get_order_status",
            {
                "order_id": "ORD-1001",
            }
        )
        # 4.判断工具是否执行失败
        if res.is_error:
            print("工具执行失败： ")
            for content in res.content:
                if isinstance(content, TextContent):
                    print(content.text)
                return

        print("\n订单查询结果：")
        print(res.structured_content)

        # 5.读取Resource
        resource = await client.read_resource(
            "policy://orders/lookup",
        )
        print("\n订单查询规范：")
        for content in resource.contents:
            if isinstance(content, TextResourceContents):
                print(content.text)

        # 6.获取Prompt
        prompt = await client.get_prompt(
            "analyze_order_issue",
            {
                "order_id": "ORD-1001",
                "symptom": "物流超过24h没有更新",
                # 填一个prompt不支持的参数会怎么样
            }
        )
        print("\n订单异常分析Prompt")
        for message in prompt.messages:
            if isinstance(message.content, TextContent):
                print(message.content.text)

if __name__ == "__main__":
    anyio.run(client_main)


# 为什么client是用异步方法，但是server是同步方法实现的