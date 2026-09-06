from pydantic import BaseModel
from langgraph.graph import START, END, StateGraph
from langchain_openai import ChatOpenAI
from core.saas_platform.models.tenant import TenantAgentConfig
from core.config import settings
from core.saas_platform.db.session import AsyncSessionLocal 
from core.saas_platform.models.tenant import Tenant, TenantAgentConfig, TokenUsageLog
from sqlalchemy import select

class AgentState(BaseModel):
    user_query: str
    answer: str
    prompt_tokens: int
    completion_tokens: int

def build_agent_with_tenant_config(tenant_cfg: TenantAgentConfig):
    llm = ChatOpenAI(
        model=tenant_cfg.model_name,
        temperature=tenant_cfg.temperature
    )
    async def agent_node(state: AgentState):
        resp = await llm.ainvoke([
            {"role":"system", "content": tenant_cfg.system_prompt},
            {"role":"user", "content": state.user_query}
        ]) 
        return {"answer": resp.content, 
                "completion_tokens": resp.response_metadata['token_usage']['completion_tokens'],
                "prompt_tokens": resp.response_metadata['token_usage']['prompt_tokens']}

    graph_builder = StateGraph(AgentState)
    graph_builder.add_node("agent_node", agent_node)
    graph_builder.add_edge(START, "agent_node")
    graph_builder.add_edge("agent_node", END)
    compiled_graph = graph_builder.compile()
    return compiled_graph

# 测试新的硅基流动api
def test_llm():
    llm = ChatOpenAI(
        model=settings.llm_model,
        timeout=settings.llm_timeout,
        base_url=settings.llm_base_url,
        api_key=settings.llm_api_key,
    )
    res = llm.invoke(["user", "你是什么模型？"])
    print(res.content)

async def add_tenant_and_config_to_table():
    async_session = AsyncSessionLocal()
    async with async_session as db:
        tenant = Tenant(
            tenant_name="Geely",
            monthly_token_quota=1_000_000,
            is_active=True
        )
        db.add(tenant)
        await db.commit()

if __name__ == "__main__":
    # import asyncio
    # asyncio.run(test_llm())
    test_llm()