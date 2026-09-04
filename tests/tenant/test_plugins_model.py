"""
创建一条公共插件记录
给测试租户绑定启动该插件
重复绑定同一个租户+插件，校验唯一约束抛出异常
查询租户已启用的全部插件列表
"""
import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy import select
from core.saas_platform.models.plugin import AgentPlugin, TenantPluginRel

async def test_create_plugin_and_bind_tenant(async_session):
    # 新建平台功能插件
    plugin = AgentPlugin(
        plugin_key="document_summary_agent",
        plugin_name="文档总结Agent",
        entry_cls="core.saas_platform.models.plugin:SummaryAgentPlugin",
        is_public=True
    )
    async_session.add(plugin)
    await async_session.commit()
    await async_session.refresh(plugin)

    # 租户启用插件
    rel = TenantPluginRel(
        tenant_id="tenant_test_001",
        plugin_id=plugin.id,
        plugin_config={"max_token": 1024}
    )
    async_session.add(rel)
    await async_session.commit()

    # 重复绑定触发唯一索引报警
    rel_dup = TenantPluginRel(
        tenant_id="tenant_test_001",
        plugin_id=plugin.id,
    )
    async_session.add(rel_dup)
    with pytest.raises(IntegrityError): # 预计这里会抛出IntegrityError, 抛出就说明通过
        await async_session.commit()
    await async_session.rollback()

    # 查询租户可用插件
    res = await async_session.execute(
        select(AgentPlugin).join(TenantPluginRel).where(TenantPluginRel.tenant_id=="tenant_test_001")
    )
    plugins = res.scalars().all()
    assert len(plugins) == 1
    assert plugins[0].plugin_key == "document_summary_agent"
