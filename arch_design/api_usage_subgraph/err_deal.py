import json
from langchain_core.tools import tool
from sqlalchemy.exc import OperationalError

# No.1: 错误处理的第一层实现
@tool
async def query_api_usage(start_date: str, end_date: str):
    """查询指定日期范围内的API调用记录"""
    try:
        rows = [
            {"date": "2026-10-05", "calls": 1000},
            {"date": "2026-10-06", "calls": 1200},
            {"date": "2026-10-07", "calls": 1300},
            {"date": "2026-10-08", "calls": 1400},
            {"date": "2026-10-09", "calls": 1500},
            {"date": "2026-10-10", "calls": 1500},
            {"date": "2026-10-11", "calls": 9200},
        ]
    except (OperationalError, TimeoutError):
        # 只处理可以明确是别的可预期错误
        # 不把所有Exception都吞掉
        # obj to str
        return json.dumps(
            {
                "ok": False,
                "error_code": "QUERY_TEMPORARY_FAILURE",
                "retryable": True,  # 不会自动触发重试，需要通过Agent提示词、重试计数或确定性的逻辑控制
                "message": (
                    "查询暂时失败，可以有限重试；"
                    "如果仍然失败，应报告任务未完成"
                ),
            },
            ensure_ascii=False
        )
    return json.dumps(
        {
            "ok": True,
            "data": rows,
        }
        ensure_ascii=False,
        default=str  # 这里default的作用是什么，不写行吗？
    )