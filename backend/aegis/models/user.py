"""User ORM model."""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from aegis.database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    username: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(
        Enum("admin", "security_officer", "auditor", "user", name="user_role"),
        nullable=False,
        default="user",
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    owned_workspaces: Mapped[list["Workspace"]] = relationship("Workspace", back_populates="owner", foreign_keys="Workspace.owner_id")
    workspace_memberships: Mapped[list["WorkspaceMember"]] = relationship("WorkspaceMember", back_populates="user")


# Avoid circular import — import at bottom
from aegis.models.workspace import Workspace, WorkspaceMember  # noqa: F401, E402
