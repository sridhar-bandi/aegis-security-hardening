"""HardeningProfile, ProfileRule, and HITLComment ORM models."""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, Float, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from aegis.database import Base


class HardeningProfile(Base):
    __tablename__ = "hardening_profiles"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(300), nullable=False)
    solution_type_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("solution_types.id", ondelete="CASCADE"), nullable=False, index=True)
    policy_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("policies.id", ondelete="SET NULL"), nullable=True)
    component_policy_map: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    status: Mapped[str] = mapped_column(
        Enum("draft", "generating", "ready", name="profile_status"),
        nullable=False,
        default="draft",
    )
    created_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    solution_type: Mapped["SolutionType"] = relationship("SolutionType", back_populates="hardening_profiles")
    policy: Mapped["Policy"] = relationship("Policy")
    profile_rules: Mapped[list["ProfileRule"]] = relationship("ProfileRule", back_populates="profile", cascade="all, delete-orphan")


class ProfileRule(Base):
    __tablename__ = "profile_rules"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    profile_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("hardening_profiles.id", ondelete="CASCADE"), nullable=False, index=True)
    policy_rule_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("policy_rules.id", ondelete="CASCADE"), nullable=False)
    component_type: Mapped[str] = mapped_column(String(100), nullable=False)
    evaluation_code: Mapped[str | None] = mapped_column(Text, nullable=True)
    remediation_code: Mapped[str | None] = mapped_column(Text, nullable=True)
    rollback_code: Mapped[str | None] = mapped_column(Text, nullable=True)
    code_status: Mapped[str] = mapped_column(
        Enum("pending", "generated", "reviewed", "approved", "rejected", name="code_status"),
        nullable=False,
        default="pending",
    )
    risk_score: Mapped[float] = mapped_column(Float, default=5.0, nullable=False)
    saved_state: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    profile: Mapped["HardeningProfile"] = relationship("HardeningProfile", back_populates="profile_rules")
    policy_rule: Mapped["PolicyRule"] = relationship("PolicyRule", back_populates="profile_rules")
    hitl_comments: Mapped[list["HITLComment"]] = relationship("HITLComment", back_populates="profile_rule", cascade="all, delete-orphan")


class HITLComment(Base):
    __tablename__ = "hitl_comments"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    profile_rule_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("profile_rules.id", ondelete="CASCADE"), nullable=False, index=True)
    author_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    comment_text: Mapped[str] = mapped_column(Text, nullable=False)
    comment_type: Mapped[str] = mapped_column(
        Enum("review", "approval", "rejection", name="comment_type"),
        nullable=False,
        default="review",
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    profile_rule: Mapped["ProfileRule"] = relationship("ProfileRule", back_populates="hitl_comments")


from aegis.models.solution_type import SolutionType  # noqa: F401, E402
from aegis.models.policy import Policy, PolicyRule  # noqa: F401, E402
