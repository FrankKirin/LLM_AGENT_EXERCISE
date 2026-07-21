import json
from core.logger import logger
from core.tools import TOOLS_MAP

def execute_tool(tool_call) -> str:
    """
    执行工具调用
    tool_call：LLM返回的tool_call对象
    return:工具返回字符串
    新版OpenAPI中用arguments表示参数，name表示方法名
    """
    raw_args = tool_call.function.arguments
    raw_tool_name = tool_call.function.name

    # 解析args参数
    try:
        args = json.loads(raw_args)
        logger.debug(f"接收到LLM函数调用的args为：{args}")
    except json.JSONDecodeError as e:
        logger.warning(f"LLM函数调用参数解析报错：{str(e)}")
        return f"LLM函数参数解析报错"

    if raw_tool_name in TOOLS_MAP:
        tool_name = TOOLS_MAP[raw_tool_name]
        logger.debug(f"LLM函数将要调用的函数为 {tool_name}")
    else:
        return f"调用的函数不在可用函数列表内"

    try:
        result = tool_name(**args)
        logger.debug(f"函数调用执行结果{result}")
        return json.dumps(result, ensure_ascii=False)
    except Exception as e:
        logger.warning("工具执行异常：tool=func_name, args=args, error=str(e)")
        return f"调用工具异常: str(e)"
