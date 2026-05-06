"""Profile schemas."""
from __future__ import annotations
import uuid
from datetime import datetime
from pydantic import BaseModel, ConfigDict


class PolicyProfileCreate(BaseModel):
    name: str
    description: str | None = None
    profile_type: str = "standard"  # "standard" | "tailored"
    included_rule_ids: list[uuid.UUID] | None = None  # required if tailored


class PolicyProfileUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    included_rule_ids: list[uuid.UUID] | None = None


class PolicyProfileResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    policy_id: uuid.UUID
    workspace_id: uuid.UUID
    name: str
    description: str | None
    version: int
    parent_version_id: uuid.UUID | None
    profile_type: str
    status: str
    included_rule_ids: list[str] | None
    created_by: uuid.UUID | None
    created_at: datetime
    locked_at: datetime | None
    rule_count: int = 0
    approved_count: int = 0
