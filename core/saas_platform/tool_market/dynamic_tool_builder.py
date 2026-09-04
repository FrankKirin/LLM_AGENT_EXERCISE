"""
从数据库读取租户自定义工具json schema+python执行代码字符串
exec在隔离局部命名空间执行代码，生成工具函数；包装城StructuredTool
"""
from langchain_core.tools import StructuredTool
from typing import Callable

def build_dynamic_tool(tool_name:str, description:str,
                       param_schema:dict,run_code:str)->StructuredTool:
    # 数据库->tool_name,description,param_schema,runnable_code
    # ->exec() -> tool_func -> StructuredTool.from_function()
    # ->LangChain Tool
    local_ns: dict[str, Callable] = {}  # 专用来接收exec()执行出来的函数
    exec(run_code, {}, local_ns)
    # 字符串中的函数函数名必须是tool_func
    func = local_ns.get("tool_func")
    if not func or not callable(func):  # 要求tool_func必须存在，并且必须真的是一个可调用的对象
        raise ValueError("Dynamic tool must define tool_func()")

    # 普通函数包装成langchain tool
    tool = StructuredTool.from_function(
        func=func,
        name=tool_name,
        description=description
    )
    return tool
