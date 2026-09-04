from core.saas_platform.tool_market.dynamic_tool_builder import build_dynamic_tool

TEST_TOOL_CODE = """
def tool_func(a:int, b:int):
    return a+b
"""

def test_dynamic_tool_builder():
    tool = build_dynamic_tool("func_to_plus", "return the result", 
                       param_schema={"a":int,"b":int},
                       run_code=TEST_TOOL_CODE)

    res = tool.invoke({"a":30, "b":20})
    assert res == 50