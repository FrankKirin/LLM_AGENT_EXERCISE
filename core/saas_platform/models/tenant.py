from datetime import datetime, timezone
from uuid import UUID, uuid4
from sqlalchemy import ForeignKey, String, Integer, DateTime, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship
from core.saas_platform.db.base import Base

class Tenant(Base):
    __tablename__="tenants"
    id:Mapped[UUID] = mapped_column(primary_key=True, default=uuid4, init=False)
    tenant_name: Mapped[str] = mapped_column(String(128))
    # 给api_key建索引
    api_key: Mapped[str] = mapped_column(String(256), unique=True, index=True)
    # 1_000_000和1000000相同，只是更容易阅读
    monthly_token_quota: Mapped[int] = mapped_column(default=1_000_000)
    is_active: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default_factory=lambda: datetime.now(timezone.utc),
        init=False) # 改为lambda表达式

class TenantAgentConfig(Base):
    __tablename__ = "tenant_agent_config"
    id:Mapped[UUID] = mapped_column(primary_key=True, default=uuid4, init=False)
    tenant_id: Mapped[UUID] = mapped_column(ForeignKey("tenants.id"), index=True)
    system_prompt: Mapped[str]
    model_name: Mapped[str] = mapped_column(default="deepseek-ai/DeepSeek-V3.2")
    temperature: Mapped[float] = mapped_column(default=0.7)

class AgentConversation(Base):
    __tablename__ = "agent_conversations"
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4, init=False)
    tenant_id: Mapped[UUID] = mapped_column(ForeignKey("tenants.id"), index=True)
    thread_id: Mapped[str] = mapped_column(String(128), index=True)
    title: Mapped[str | None] = mapped_column(String(256), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default_factory=lambda:datetime.now(timezone.utc),
        init=False
    )

class TokenUsageLog(Base):
    # 表名
    __tablename__ = "token_usage_log"
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4, init=False)
    # 租户id
    tenant_id:Mapped[UUID] = mapped_column(ForeignKey("tenants.id"), index=True)
    # thread_id
    thread_id: Mapped[str]
    # token消耗量:prompt_tokens和completion_tokens
    prompt_tokens: Mapped[int]
    completion_tokens: Mapped[int]
    # 创建时间
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default_factory=lambda:datetime.now(timezone.utc),
        init=False
    )
