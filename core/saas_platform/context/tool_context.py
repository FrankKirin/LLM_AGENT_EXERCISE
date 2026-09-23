from pydantic import BaseModel
from uuid import UUID

class ToolContext(BaseModel):
    """
        系统提供给Tool的上下文；
    """
    tenant_id: UUID
    user_id: str | None = None
    session_id: str | None = None