# LangGraph的Store接口实现租户隔离，namespace带上tenant_id
# 不同租户即使thread_id完全一致，数据互不干扰
from langgraph.store.base import BaseStore
from langgraph.store.memory import InMemoryStore
from uuid import UUID

def build_tenant_namespace(tenant_id: UUID, thread_id: str):
    """构造隔离命名空间:(tenant_uuid, thread_id)"""
    return (str(tenant_id), thread_id)

def get_default_store() -> BaseStore:
    return InMemoryStore()
