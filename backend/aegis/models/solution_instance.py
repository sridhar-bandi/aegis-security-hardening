"""SolutionInstance ORM model."""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from aegis.database import Base


class SolutionInstance(Base):
    __tablename__ = "solution_instances"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workspace_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(300), nullable=False)
    solution_type_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("solution_types.id", ondelete="SET NULL"), nullable=True)
    blueprint_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("hardening_blueprints.id", ondelete="SET NULL"), nullable=True)
    config_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    scid_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    scid_filename: Mapped[str | None] = mapped_column(String(500), nullable=True)
    owner_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    workspace: Mapped["Workspace"] = relationship("Workspace", back_populates="solution_instances")
    solution_type: Mapped["SolutionType"] = relationship("SolutionType", back_populates="solution_instances")
    blueprint: Mapped["HardeningBlueprint"] = relationship("HardeningBlueprint")
    enforcement_jobs: Mapped[list["EnforcementJob"]] = relationship("EnforcementJob", back_populates="instance", cascade="all, delete-orphan")
    compliance_reports: Mapped[list["ComplianceReport"]] = relationship("ComplianceReport", back_populates="instance", cascade="all, delete-orphan")


from aegis.models.workspace import Workspace  # noqa: F401, E402
from aegis.models.solution_type import SolutionType  # noqa: F401, E402
from aegis.models.hardening_blueprint import HardeningBlueprint  # noqa: F401, E402
from aegis.models.enforcement_job import EnforcementJob  # noqa: F401, E402
from aegis.models.compliance_report import ComplianceReport  # noqa: F401, E402
