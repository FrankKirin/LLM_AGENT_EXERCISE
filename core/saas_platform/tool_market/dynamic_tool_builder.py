"""
从数据库读取租户自定义工具json schema+python执行代码字符串
exec在隔离局部命名空间执行代码，生成工具函数；包装城StructuredTool
"""
import inspect
import asyncio
from langchain_core.tools import StructuredTool, ToolException
from jsonschema import validate
from jsonschema.exceptions import ValidationError, SchemaError
from jsonschema import Draft202012Validator
from core.saas_platform.context.tool_context import ToolContext

async def build_dynamic_tool(tool_name:str, description: str,
                       run_code:str, param_schema:dict,
                       context:ToolContext)->StructuredTool:
    """
        param_schema: 标准JSON Schema
        system_context: 系统注入参数，不暴露给LLM
        {
            "tenant_id": "tenand_001"
        }
    """
    # 校验param_schema
    if not isinstance(param_schema, dict):
        raise TypeError("param_schema必须是dict")
    if param_schema.get("type") != "object":
        raise ValueError("param_schema顶层type必须是object")

    # 检查JSON Schema是否合法, 用Draft202012Validator
    try:
        # validate(instance={}, schema=param_schema)
        Draft202012Validator.check_schema(param_schema)
    except SchemaError as e:
        raise ValueError(
            f"Tool {tool_name}的JSON Schema非法: {e.message}"
        ) from e

    namespace = {}
    try:
        exec(run_code, namespace)
    except Exception as e:
        raise ValueError(
            f"Tool{tool_name}的run_code执行失败：{e}"
        )
    tool_func = namespace["tool_func"]

    func = namespace["tool_func"]
    if not func or not callable(func):  # 要求tool_func必须存在，并且必须真的是一个可调用的对象
        raise ValueError("Dynamic tool must define as tool_func()")

    async def ayc_tool_runner(**kwargs):
        """
        kwargs: Agent参数
        """
        # 用来校验传进来的data是否符合param_schema规范
        try:
            validate(
                instance=kwargs,
                schema=param_schema,
            )
        except ValidationError as e:
            raise ToolException(
                f"Tool '{tool_name}'参数不合法：{e.message}"
            )from e

        final_kwargs = dict(kwargs) 
        # 根据tool_func是否声明了context，不要无脑传context
        sig = inspect.signature(tool_func)

        if "context" in sig.parameters:
            final_kwargs["context"] = context

        try:
            if inspect.iscoroutinefunction(tool_func):
                return await tool_func(**final_kwargs)
            else:
                return await asyncio.to_thread(
                    tool_func,
                    **final_kwargs,
                )
        except ToolException:
            raise
        except Exception as e:
            raise ToolException(
                f"Tool '{tool_name}'执行失败：{e}"
            ) from e
    return StructuredTool.from_function(
        coroutine=ayc_tool_runner,
        name=tool_name,
        description=description,
        args_schema=param_schema,
        infer_schema=False,
        handle_tool_error=True,
    )

# if __name__ == "__main__":
#     tenant_id = "b7c84a42f0e941d29943d4f5e6f0f9da"
#     context_data = ToolContext(tenant_id=tenant_id)
#     print("Content of context data: {context_data}")

#     mock_sync_param_schema1 = {
#     "type": "object",
#     "properties": {
#         "city": {
#             "type": "string",
#             "description": "城市名称，只支持Shanghai、Beijing"
#         },
#     },
#     "required": ["city"]
# }
#     run_code1 = textwrap.dedent("""
#     def tool_func(city:str="Shanghai"):
#         data = {"Shanghai": "34C", "Beijing": "28C"}
#         res = data.get(city)
#         return res if res else "你所查询的城市天气数据不存在"
#     """).strip()

#     desc1 = "查询指定城市的天气"

#     import asyncio
#     tool1 = asyncio.run(build_dynamic_tool("fetch_weather", desc1,
#                        run_code=run_code1, param_schema=mock_sync_param_schema1,
#                        context=context_data))

#     res1 = asyncio.run(tool1.ainvoke({
#         "city":"Shanghai"
#     }))
#     print(res1)

#     assert res1=="34C", "tool1输出结果与预期不符"

#     mock_sync_param_schema2 = {
#     "type": "object",
#     "properties": {
#         "a": {
#             "type": "integer",
#             "description": "相加的数"
#         },
#         "b": {
#             "type": "integer",
#             "description": "相加的数"
#         },
#     },
#     "required": ["a", "b"]
# }
#     # 场景2
#     run_code2 = textwrap.dedent("""
#         def tool_func(a:int, b:int):
#             return a+b
#     """).strip()

#     desc2 = "将两整数相加结果返回"


#     mock_sync_param_schema3 = {
#     "type": "object",
#     "properties": {},
# }

#     import asyncio
#     tool2 = asyncio.run(build_dynamic_tool("fetch_calculate_result", desc2,
#                        run_code=run_code2, param_schema=mock_sync_param_schema2,
#                        context=context_data))
#     res = asyncio.run(
#         tool2.ainvoke({
#             "a":10, "b":50
#         })
#     )
#     print(f"tool2的输出结果为{res}")
#     assert res==60, "tool2输出结果与预期不符"

#     # 场景3
    run_code3 = textwrap.dedent("""
    from uuid import UUID
    from core.saas_platform.models.storage import StorageInfo
    from sqlalchemy import select
    from core.saas_platform.db.session import AsyncSessionLocal
    async def tool_func(context)->int:    
        async with AsyncSessionLocal() as db:        
            tenant_id = UUID(context.tenant_id)
            rows = await db.execute(select(StorageInfo).where(StorageInfo.tenant_id == tenant_id))
            res = rows.scalar_one_or_none()        
            return res.remaining_space if res else 0
    """).strip()

#     desc3 = "根据用户tenant_id查询剩余可用云盘空间"

#     import asyncio
#     tool3 = asyncio.run(build_dynamic_tool("fetch_storage", desc3,
#                        run_code=run_code3, param_schema=mock_sync_param_schema3,
#                        context=context_data))

#     res = asyncio.run(tool3.ainvoke(
#         {}
#     ))

#     print(f"tool3的输出结果为{res}")


