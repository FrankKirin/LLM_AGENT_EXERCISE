from core.saas_platform.tool_market.dynamic_tool_builder import build_dynamic_tool

TEST_TOOL_CODE = """
def tool_func(a:int, b:int):
    return a+b
"""

"""
def build_dynamic_tool(tool_name:str, description:str,
                       param_schema:dict,run_code:str)->StructuredTool:
    # 数据库->tool_name,description,param_schema,runnable_code
    # ->exec() -> tool_func -> StructuredTool.from_function()
    # ->LangChain Tool
    local_ns: dict[str, Callable] = {}  # 专用来接收exec()执行出来的函数
    exec(run_code, {}, local_ns)
    # 字符串中的函数名必须是tool_func
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
"""

def test_dynamic_tool_builder():
    tool = build_dynamic_tool("func_to_plus", "return the result", 
                       param_schema={"a":int,"b":int},
                       run_code=TEST_TOOL_CODE)
    res = tool.invoke({"a":30, "b":20})
    assert res == 50