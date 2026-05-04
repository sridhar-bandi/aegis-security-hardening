"""Policy schemas."""
from __future__ import annotations
import uuid
from datetime import datetime
from typing import Any
from pydantic import BaseModel, ConfigDict


class PolicyResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    workspace_id: uuid.UUID
    name: str
    description: str | None
    standard: str
    format: str
    created_at: datetime


class PolicyRuleResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    policy_id: uuid.UUID
    rule_id: str
    title: str
    description: str | None
    rationale: str | None
    severity: str
    category: str | None
    target_component_types: list[str] | None
    check_content: str | None
    fix_text: str | None
    created_at: datetime


class PolicyImportRequest(BaseModel):
    source: str  # "github" | "sharepoint" | "confluence"
    url: str
    token: str | None = None
    workspace_id: uuid.UUID
    name: str
    standard: str = "Custom"
