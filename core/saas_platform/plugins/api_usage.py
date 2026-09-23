from typing import Any
from datetime import datetime, timezone, timedelta
from sqlalchemy import select, func
from core.saas_platform.context.tool_context import ToolContext
from core.saas_platform.db.session import AsyncSessionLocal
from core.saas_platform.models.tenant import TokenUsageLog
from core.saas_platform.plugins.base_plugin import BaseAgentPlugin
from langgraph.graph import StateGraph, START, END
from typing import TypedDict
from langgraph.runtime import Runtime

class ApiUsageState(TypedDict):
    result: list[dict]

class ApiUsage(BaseAgentPlugin):
    def __init__(self, plugin_config: dict):
        super().__init__(plugin_config)

    def build_sub_graph(self) -> tuple[str, Any]:
        async def get_token_usage(
                state: ApiUsageState,
                runtime: Runtime[ToolContext],
            ):
            to = datetime.now(timezone.utc).date()
            from_ = to - timedelta(days=6)
            async with AsyncSessionLocal() as db:
                print(f"runtime的context内容:{runtime.context}")
                tenant_id = runtime.context.tenant_id

                stmt = (
                    select(
                        # label就是给字段取个名字，方便取值，例如row.date
                        func.date(TokenUsageLog.created_at).label("date"),
                        func.sum(TokenUsageLog.completion_tokens 
                                + TokenUsageLog.prompt_tokens).label("total_tokens"),
                    ).where(
                        TokenUsageLog.tenant_id == tenant_id,
                        TokenUsageLog.created_at >= from_
                    )
                    .group_by(func.date(TokenUsageLog.created_at))
                    .order_by(func.date(TokenUsageLog.created_at))
                )

                rows = (await db.execute(stmt)).all() # {(created_at, total_sum)}
                results = { str(row[0]):row[1] for row in rows}
            existed_date = [str(d) for d in results]
            trend = [] # ["date":"", "usage": xxx]
            for i in range(7):
                date = str(from_ + timedelta(days=i))
                trend.append({"date":date, 
                              "usage": 0 if date not in existed_date else results.get(date)})
            # 返回字典，框架会自动把字典更新到state
            return {"result": trend}

        graph = StateGraph(
            ApiUsageState,
            context_schema=ToolContext,
        )
        graph.add_node("token_usage", get_token_usage)

        graph.add_edge(START, "token_usage")
        graph.add_edge("token_usage", END)

        compiled_graph = graph.compile()

        return "api_usage", compiled_graph

if __name__ == "__main__":
    import asyncio
    apiusage = ApiUsage({})
    name, graph = apiusage.build_sub_graph()
    res = asyncio.run(graph.ainvoke({
        "trend":"",
    }))
    print(res)