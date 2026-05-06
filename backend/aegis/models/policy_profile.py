"""PolicyProfile ORM model."""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from aegis.database import Base


class PolicyProfile(Base):
    __tablename__ = "policy_profiles"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    policy_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("policies.id", ondelete="CASCADE"), nullable=False, index=True)
    workspace_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(300), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default="1")
    parent_version_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("policy_profiles.id"), nullable=True)
    profile_type: Mapped[str] = mapped_column(
        Enum("standard", "tailored", name="profile_type", create_type=False),
        nullable=False, default="standard", server_default="standard",
    )
    status: Mapped[str] = mapped_column(
        Enum("draft", "in_review", "approved", "locked", name="profile_status", create_type=False),
        nullable=False, default="draft", server_default="draft",
    )
    included_rule_ids: Mapped[list | None] = mapped_column(JSON, nullable=True)
    created_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    locked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    policy: Mapped["Policy"] = relationship("Policy", back_populates="profiles")
    workspace: Mapped["Workspace"] = relationship("Workspace")
    parent_version: Mapped["PolicyProfile | None"] = relationship("PolicyProfile", remote_side="PolicyProfile.id")


from aegis.models.policy import Policy  # noqa: F401, E402
from aegis.models.workspace import Workspace  # noqa: F401, E402
