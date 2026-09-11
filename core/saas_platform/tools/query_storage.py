from langchain_core.tools import StructuredTool
from sqlalchemy import select
from core.saas_platform.db.session import AsyncSessionLocal
from core.saas_platform.models.storage import StorageInfo
from uuid import UUID
from pydantic import BaseModel, Field

# Pydantic参数模型, description很重要，会成为工具参数的说明，帮助LLM知道tenant_id是什么
class QueryStorageInput(BaseModel):
    tenant_id:str = Field(
        description="租户的唯一标识UUID"
    )

async def query_storage(tenant_id:UUID):
    async with AsyncSessionLocal() as db:
        records = await db.execute(select(StorageInfo).where(StorageInfo.tenant_id==tenant_id))
        res = records.scalar_one_or_none()
        if not res:
            return {"error": "storage record not found"}
        return {
            "total_space": res.total_space,
            "used_space": res.used_space,
            "remaining_space": res.remaining_space,
        }

# 供别人调用的工具需要精心打磨description
query_storage_tool = StructuredTool.from_function(
    coroutine=query_storage,
    name="query_storage",
    description=(
        "查询指定租户的存储使用情况，返回总空间，已用空间、剩余空间"
    ),
    args_schema=QueryStorageInput,
)