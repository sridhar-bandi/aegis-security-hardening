"""ComplianceReport ORM model."""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from aegis.database import Base


class ComplianceReport(Base):
    __tablename__ = "compliance_reports"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    instance_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("solution_instances.id", ondelete="CASCADE"), nullable=False, index=True)
    job_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("enforcement_jobs.id", ondelete="SET NULL"), nullable=True)
    report_type: Mapped[str] = mapped_column(
        Enum("arf", "html", "summary", name="report_type"),
        nullable=False,
        default="arf",
    )
    file_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    summary: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    instance: Mapped["SolutionInstance"] = relationship("SolutionInstance", back_populates="compliance_reports")
    job: Mapped["EnforcementJob"] = relationship("EnforcementJob", back_populates="compliance_reports")


from aegis.models.solution_instance import SolutionInstance  # noqa: F401, E402
from aegis.models.enforcement_job import EnforcementJob  # noqa: F401, E402
