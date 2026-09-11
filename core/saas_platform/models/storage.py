from datetime import datetime, timezone
from uuid import UUID
from sqlalchemy import ForeignKey, String, Integer, DateTime, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship
from core.saas_platform.db.base import Base

class StorageInfo(Base):
    __tablename__="storage_info"
    id: Mapped[int] = mapped_column(autoincrement=True, primary_key=True, init=False)
    tenant_id: Mapped[UUID] = mapped_column(ForeignKey("tenants.id"), index=True, unique=True)
    total_space: Mapped[int] = mapped_column(default=1_000_000_000)
    used_space: Mapped[int] = mapped_column(default=0)

    @property
    def remaining_space(self) -> int:
        return self.total_space - self.used_space

    @property
    def usage_percent(self) -> float:
        if self.total_space == 0:
            return 0
        return round(self.used_space / self.total_space * 100, 2)

    def has_capacity(self, required_space: int, buffer_ratio: float=0.95) -> bool:
        return (self.used_space + required_space) <= self.total_space * buffer_ratio
