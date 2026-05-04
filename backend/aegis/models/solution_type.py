"""SolutionType ORM model."""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from aegis.database import Base


class SolutionType(Base):
    __tablename__ = "solution_types"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workspace_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    config_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    component_selection: Mapped[list | None] = mapped_column(JSON, nullable=True)
    created_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    workspace: Mapped["Workspace"] = relationship("Workspace", back_populates="solution_types")
    hardening_profiles: Mapped[list["HardeningProfile"]] = relationship("HardeningProfile", back_populates="solution_type")
    solution_instances: Mapped[list["SolutionInstance"]] = relationship("SolutionInstance", back_populates="solution_type")


from aegis.models.workspace import Workspace  # noqa: F401, E402
from aegis.models.hardening_profile import HardeningProfile  # noqa: F401, E402
from aegis.models.solution_instance import SolutionInstance  # noqa: F401, E402
