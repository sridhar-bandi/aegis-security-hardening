"""Policy and PolicyRule ORM models."""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from aegis.database import Base


class Policy(Base):
    __tablename__ = "policies"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workspace_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(300), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    standard: Mapped[str] = mapped_column(
        Enum("CIS", "STIG", "SRG", "Custom", name="policy_standard"),
        nullable=False,
        default="Custom",
    )
    format: Mapped[str] = mapped_column(
        Enum("OVAL", "XCCDF", "text", "json", name="policy_format"),
        nullable=False,
        default="text",
    )
    file_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    code_status: Mapped[str] = mapped_column(
        Enum("pending", "generating", "generated", "reviewed", "approved", "rejected", name="code_status"),
        nullable=False,
        default="pending",
    )
    created_by: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    workspace: Mapped["Workspace"] = relationship("Workspace", back_populates="policies")
    rules: Mapped[list["PolicyRule"]] = relationship("PolicyRule", back_populates="policy", cascade="all, delete-orphan")


class PolicyRule(Base):
    __tablename__ = "policy_rules"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    policy_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("policies.id", ondelete="CASCADE"), nullable=False, index=True)
    rule_id: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    rationale: Mapped[str | None] = mapped_column(Text, nullable=True)
    severity: Mapped[str] = mapped_column(
        Enum("critical", "high", "medium", "low", "informational", name="rule_severity"),
        nullable=False,
        default="medium",
    )
    category: Mapped[str | None] = mapped_column(String(100), nullable=True)
    target_component_types: Mapped[list | None] = mapped_column(JSON, nullable=True)
    check_content: Mapped[str | None] = mapped_column(Text, nullable=True)
    fix_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    # LLM-generated code stored at the policy rule level (canonical / baseline)
    evaluation_code: Mapped[str | None] = mapped_column(Text, nullable=True)
    remediation_code: Mapped[str | None] = mapped_column(Text, nullable=True)
    rollback_code: Mapped[str | None] = mapped_column(Text, nullable=True)
    code_status: Mapped[str] = mapped_column(
        Enum("pending", "generating", "generated", "reviewed", "approved", "rejected", name="code_status"),
        nullable=False,
        default="pending",
    )
    milvus_embedding_id: Mapped[str | None] = mapped_column(String(200), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    policy: Mapped["Policy"] = relationship("Policy", back_populates="rules")
    profile_rules: Mapped[list["ProfileRule"]] = relationship("ProfileRule", back_populates="policy_rule")


from aegis.models.workspace import Workspace  # noqa: F401, E402
from aegis.models.hardening_profile import ProfileRule  # noqa: F401, E402
