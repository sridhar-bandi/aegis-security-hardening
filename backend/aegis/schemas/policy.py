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
    code_status: str
    created_at: datetime
    rule_count: int = 0
    target_component_types: list[str] = []


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
    # LLM-generated baseline code fields
    evaluation_code: str | None
    remediation_code: str | None
    rollback_code: str | None
    code_status: str
    # Review/import tracking fields
    code_source: str = "llm"
    imported_filename: str | None = None
    reviewed_by: uuid.UUID | None = None
    reviewed_at: datetime | None = None
    created_at: datetime


class PolicyRuleCodeUpdate(BaseModel):
    evaluation_code: str | None = None
    remediation_code: str | None = None
    rollback_code: str | None = None


class PolicyRuleRejectRequest(BaseModel):
    reason: str | None = None


class PolicyImportRequest(BaseModel):
    source: str  # "github" | "sharepoint" | "confluence"
    url: str
    token: str | None = None
    workspace_id: uuid.UUID
    name: str
    standard: str = "Custom"


class PolicyCodeGenRequest(BaseModel):
    rule_ids: list[uuid.UUID] | None = None
