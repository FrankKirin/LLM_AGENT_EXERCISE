"""
从数据库读取租户自定义工具json schema+python执行代码字符串
exec在隔离局部命名空间执行代码，生成工具函数；包装城StructuredTool
"""
import inspect
from langchain_core.tools import StructuredTool
from functools import partial
from typing import Any, Literal
from uuid import UUID


def build_dynamic_tool(tool_name:str, description: str,
                       run_code:str, args_schema:type,
                       context:dict)->StructuredTool:
    namespace = {}
    exec(run_code, namespace)

    tool_func = namespace["tool_func"]

    func = namespace["tool_func"]
    if not func or not callable(func):  # 要求tool_func必须存在，并且必须真的是一个可调用的对象
        raise ValueError("Dynamic tool must define as tool_func()")

    async def tool_runner(**kwargs):
        return await tool_func(
            kwargs,
            context,
        )

    return StructuredTool.from_function(
        coroutine=tool_runner,
        name=tool_name,
        description=description,
        args_schema=args_schema,
    )

if __name__ == "__main__":
    pass