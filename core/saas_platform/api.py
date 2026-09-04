import json
from uuid import UUID
from fastapi import APIRouter, Header, Depends, HTTPException, status
from core.saas_platform.auth import verify_tenant, check_token_quota
from core.saas_platform.db.session import get_db
from core.saas_platform.db.models import TenantAgentConfig, TokenUsageLog
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from fastapi.responses import StreamingResponse
from core.saas_platform.db.models import Tenant
from core.saas_platform.graph.agent_graph import build_agent_with_tenant_config 
from core.structured_logger import log_info

router = APIRouter(prefix="/saas", tags=["API service for SasS User"])

@router.post("/create_tenant")
async def create_tenant(tenant_name:str, x_tenant_api_key:str=Header("X-Tenant-Api-Key"), db:AsyncSession=Depends(get_db)):
    tenant = Tenant(
        tenant_name=tenant_name,
        api_key=x_tenant_api_key,
        is_active=True,
    )
    db.add(tenant)
    await db.commit()
    await db.refresh(tenant)
    log_info(f"租户:{x_tenant_api_key}写入成功")
    return {
        "id": str(tenant.id),
        "tenant_name": tenant.tenant_name,
        "api_key": tenant.api_key,
    }

@router.post("/add_or_update_agent_config")
async def update_agent_config(system_prompt:str=None,
                              x_tenant_api_key:str = Header(..., alias="X-TENANT-API-KEY"), # ...表示没有默认值/必填，alias指定从哪个Header取值
                              temperature:float=0.7, db:AsyncSession = Depends(get_db),
                              model_name:str="deepseek-ai/DeepSeek-V3.2"):
    stmt = select(Tenant).where(Tenant.api_key==x_tenant_api_key)
    temp = await db.execute(stmt)
    tenant = temp.scalar_one_or_none()
    if not tenant:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="未找到指定的Tenant")

    print(f"----找到Tenant_ID----{tenant.id}")
    result = await db.execute(
        select(TenantAgentConfig).where(TenantAgentConfig.tenant_id==tenant.id)
    )
    agent_config = result.scalar_one_or_none()
    # 找不到就添加一个
    if not agent_config:
        new_tenant = TenantAgentConfig(
            model_name=model_name,
            system_prompt=system_prompt,
            temperature=temperature,
            tenant_id=tenant.id,
        )
        db.add(new_tenant) # add是同步方法
        await db.commit()
        await db.refresh(new_tenant)
        return new_tenant
    # 找到就更新
    if model_name:
        agent_config.model_name = model_name
    if system_prompt:
        agent_config.system_prompt = system_prompt
    if temperature:
        agent_config.temperature = temperature

    await db.commit()
    await db.refresh(agent_config)
    return agent_config

@router.post("/agent/stream")
async def agent_system(user_query:str,
                       thread_id:str,
                       x_tenant_api_key:str=Header("X-Tenant-Api-Key"),
                       db:AsyncSession=Depends(get_db)):
    """
    处理：
        验证租户id是否合法（存在，是否激活状态），是否还有剩余token配额
        是否配置了Agent参数
    """
    tenant = await verify_tenant(x_tenant_api_key, db)
    if not await check_token_quota(tenant.id, db):
        # StreamingResponse第一个参数必须是个可迭代对象
        return StreamingResponse(iter(['data:{"error":"月度token配额耗尽"}\n\n']), media_type="text/event-stream")
    stmt = select(TenantAgentConfig).where(TenantAgentConfig.tenant_id == tenant.id)
    execute_res = await db.execute(stmt)
    tenant_cfg = execute_res.scalar_one_or_none()
    if not tenant_cfg:  # 是否要考虑tenant_cfg为None的情况
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="用户未配置Agent参数")

    graph = build_agent_with_tenant_config(tenant_cfg)
    async def generate_res():
        completion_tokens = 0
        prompt_tokens = 0
        async for chunk in graph.astream({"user_query": user_query}):
            agent_result = chunk.get("agent_node")
            if agent_result:
                completion_tokens = agent_result.get("completion_tokens", 0)
                prompt_tokens = agent_result.get("prompt_tokens", 0)
                print("completion_tokens", completion_tokens)
                print("prompt_tokens", prompt_tokens)

            yield f"data: {json.dumps(chunk)}\n\n"  # SSE对每个事件的格式要求
        log_entry = TokenUsageLog(
            tenant_id=tenant.id,
            thread_id=thread_id,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
        )
        db.add(log_entry)
        await db.commit()

    return StreamingResponse(generate_res(), media_type="text/event-stream")
        

    