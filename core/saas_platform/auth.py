import asyncio
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from core.saas_platform.db.session import AsyncSessionLocal
from core.saas_platform.db.models import Tenant, TokenUsageLog
from uuid import UUID
from sqlalchemy import select, func
from datetime import datetime

async def verify_tenant(api_key: str, db: AsyncSession):
    sql_state = select(Tenant).where(Tenant.api_key == api_key, Tenant.is_active==True)
    result = await db.execute(sql_state)
    tenant = result.scalar_one_or_none()  # 从查询结果中取出唯一一条对象，没有结果返回None，出现多条则报错
    if not tenant:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="租户密钥无效或租户已停用")
    return tenant

async def check_token_quota(tenant_id: UUID, db: AsyncSession)->bool:
    # 只查出tenant obj
    stmt = select(Tenant).where(Tenant.id == tenant_id)  # 不要漏掉Tenant状态必须是active
    tenant_obj = (await db.execute(stmt)).scalar_one()

    now = datetime.utcnow()
    start_of_month = datetime(year=now.year, month=now.month, day=1)  # 拿到当前年和月
    sql_state = select(func.sum(TokenUsageLog.prompt_tokens + TokenUsageLog.completion_tokens)).where(TokenUsageLog.tenant_id == tenant_id)\
                .where(TokenUsageLog.created_at >= start_of_month)
    res = await db.execute(sql_state)
    used_token = res.scalar() or 0  # scalar()从查询结果中取第一行的第一个字段

    return used_token < tenant_obj.monthly_token_quota
