from core.saas_platform.db.base import Base
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import (ForeignKey, JSON, Boolean, 
                        String, DateTime, UniqueConstraint,func)
from typing import Any
from dataclasses import field
from datetime import datetime, timezone

class AgentPlugin(Base):
    __tablename__ = "agent_plugin"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True, init=False)
    # 虽然写了index=True，但是很多数据库如果unique=True就会创建唯一索引
    plugin_key: Mapped[str] = mapped_column(String(128), unique=True, index=True, comment="插件唯一编码")
    plugin_name: Mapped[str] = mapped_column(String(128))
    entry_cls: Mapped[str] = mapped_column(String(256), comment="动态加载入口类路径")
    # 数据库把字典存成JSON, 灵活应对,不同插件配置的情况
    config_schema: Mapped[dict[str, Any]] = mapped_column(JSON, default_factory=dict)
    is_public: Mapped[bool] = mapped_column(Boolean, default=False, comment="是否全租户可用")
    # 数据库端生成
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default_factory=lambda:datetime.now(timezone.utc),
        init=False
    )

class TenantPluginRel(Base):
    __tablename__ = "tenant_plugin_rel"
    id:Mapped[int] = mapped_column(primary_key=True, init=False)
    tenant_id:Mapped[str] = mapped_column(String(64), index=True)
    plugin_id:Mapped[int] = mapped_column(ForeignKey("agent_plugin.id"))
    # 这个租户实际配置成什么
    plugin_config: Mapped[dict[str, Any]] = mapped_column(JSON, default_factory=dict)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    __table_args__ = (UniqueConstraint("tenant_id", "plugin_id", name="uniq_tenant_plugin"),)

class CustomTool(Base):
    # 租户自己定义的Agent Tool
    __tablename__ = "tenant_tool"
    id:Mapped[int] = mapped_column(primary_key=True)
    tenant_id:Mapped[str] = mapped_column(String(64), index=True)
    tool_name:Mapped[str] = mapped_column(String(128))
    description: Mapped[str] = mapped_column(String(512))
    param_schema: Mapped[dict[str, Any]] = mapped_column(JSON)  # 定义tool接收什么参数，参数是什么类型
    runnable_code:Mapped[str] = mapped_column(JSON, comment="工具执行代码字符串") # 租户自定义tool的执行逻辑用代码字符串形式保存
    enabled:Mapped[bool] = mapped_column(Boolean, default=True)
    created_at:Mapped[datetime]= mapped_column(DateTime(timezone=True),
                                               default_factory=lambda: datetime.now(timezone.utc),
                                               init=False)
