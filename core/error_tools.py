from langchain_core.tools import tool

@tool
def bad_tool(param: str)-> str:
    """测试专用的异常工具，用于测试报错处理流程。
    """
    raise RuntimeError("模拟网络连接超时或数据库崩溃")