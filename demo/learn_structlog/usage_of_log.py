import structlog
import json

logger = structlog.get_logger()

def execute_agent_task(user_id: str, query: str):

    # warning用于记录 ”自愈性异常“
    # 发生了意外，但是有容错兜底方案
    try:
        llm_raw_output = '{"need_call": true, "tool_name": "query_db"'
        res = json.loads(llm_raw_output)

    except json.JSONDecodeError as e:
        logger.warning(
            "llm_json_damaged_but_handled",
            error_msg=str(e),
            raw_output = llm_raw_output
        )

execute_agent_task("12399", "test")

# 看变量、看 Prompt ➡️ DEBUG

# 记流程、记成功 ➡️ INFO

# 出小状况但死里逃生 ➡️ WARNING

# 这次用户的请求彻底搞砸了 ➡️ ERROR

# 整个项目崩了/要被迫停机了 ➡️ CRITICAL