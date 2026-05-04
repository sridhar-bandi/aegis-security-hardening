"""Workspace schemas."""
from __future__ import annotations
import uuid
from datetime import datetime
from pydantic import BaseModel, ConfigDict


class WorkspaceCreate(BaseModel):
    name: str
    description: str | None = None


class WorkspaceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    description: str | None
    owner_id: uuid.UUID
    created_at: datetime


class WorkspaceMemberAdd(BaseModel):
    user_id: uuid.UUID
    role: str = "user"
