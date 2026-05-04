"""EnforcementJob ORM model."""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from aegis.database import Base


class EnforcementJob(Base):
    __tablename__ = "enforcement_jobs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    instance_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("solution_instances.id", ondelete="CASCADE"), nullable=False, index=True)
    job_type: Mapped[str] = mapped_column(
        Enum("evaluate", "remediate", "rollback", "dry_run", "impact_assessment", name="job_type"),
        nullable=False,
    )
    status: Mapped[str] = mapped_column(
        Enum("pending", "running", "completed", "failed", name="job_status"),
        nullable=False,
        default="pending",
    )
    celery_task_id: Mapped[str | None] = mapped_column(String(200), nullable=True)
    result_summary: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    instance: Mapped["SolutionInstance"] = relationship("SolutionInstance", back_populates="enforcement_jobs")
    compliance_reports: Mapped[list["ComplianceReport"]] = relationship("ComplianceReport", back_populates="job")


from aegis.models.solution_instance import SolutionInstance  # noqa: F401, E402
from aegis.models.compliance_report import ComplianceReport  # noqa: F401, E402
