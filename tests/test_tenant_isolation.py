import pytest
from sqlalchemy import select
from core.saas_platform.models.tenant import Tenant
from core.saas_platform.db.session import get_db

@pytest.mark.asyncio
async def test_two_tenant_separate():
    async for db in get_db():
        t1 = Tenant(tenant_name="企业A", api_key="key‑a‑001", monthly_token_quota=10000)
        t2 = Tenant(tenant_name="企业B", api_key="key‑b‑001", monthly_token_quota=10000)
        db.add_all([t1,t2])
        await db.commit()
        res_a = await db.execute(select(Tenant).where(Tenant.api_key == "key‑a‑001"))
        assert res_a.scalar_one().tenant_name == "企业A"
