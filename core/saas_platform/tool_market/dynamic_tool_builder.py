"""
从数据库读取租户自定义工具json schema+python执行代码字符串
exec在隔离局部命名空间执行代码，生成工具函数；包装城StructuredTool
"""
import inspect
import asyncio
from langchain_core.tools import StructuredTool, ToolException
from functools import partial
from typing import Any, Literal
from uuid import UUID
from dataclasses import dataclass
from pydantic import BaseModel, create_model
from jsonschema import validate
from jsonschema.exceptions import ValidationError, SchemaError


@dataclass
class ToolContext:
    """
        系统提供给Tool的上下文；
    """
    tenant_id: str
    user_id: str | None
    session_id: str | None

async def build_dynamic_tool(tool_name:str, description: str,
                       run_code:str, param_schema:dict,
                       system_context:dict={})->StructuredTool:
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

    # 检查JSON Schema是否合法
    try:
        validate(instance={}, schema=param_schema)
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
        context: 系统参数
        """
        try:
            validate(
                instance=kwargs,
                schema=param_schema,
            )
        except ValidationError as e:
            raise ToolException(
                f"Tool '{tool_name}'参数不合法：{e.message}"
            )from e

        # 合并系统参数
        final_kwargs = {
            **kwargs,
            **(system_context or {})
        }

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

if __name__ == "__main__":
    mock_sync_param_schema = {
    "type": "object",
    "properties": {
        "city": {
            "type": "string",
            "description": "城市名称，只支持Shanghai、Beijing"
        },
    },
    "required": ["city"]
}
    run_code = """
    def tool_func(city:str="Shanghai"):
        data = {"Shanghai": "34C", "Beijing": "28C"}
        res = data.get(city)
        return res if res else "你所查询的城市天气数据不存在"
    """
    import asyncio
    tool = asyncio.run(build_dynamic_tool("fetch_weather", "工具根据城市返回实时气温",
                       run_code=run_code, param_schema=mock_sync_param_schema))

    print(asyncio.run(tool.ainvoke({
        "city":"Shanghai"
    })))


