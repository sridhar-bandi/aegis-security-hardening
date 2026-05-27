"""Hardening profile schemas."""
from __future__ import annotations
import uuid
from datetime import datetime
from pydantic import BaseModel, ConfigDict


class HardeningProfileCreate(BaseModel):
    name: str
    solution_type_id: uuid.UUID
    # Maps each component_type (string) to the policy_id (UUID) that governs it.
    # e.g. {"server": "<policy-uuid>", "network_switch": "<policy-uuid>"}
    component_policy_map: dict[str, uuid.UUID]


class HardeningProfileResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    solution_type_id: uuid.UUID
    policy_id: uuid.UUID | None
    component_policy_map: dict | None
    status: str
    created_at: datetime


class ProfileRuleResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    profile_id: uuid.UUID
    policy_rule_id: uuid.UUID
    component_type: str
    evaluation_code: str | None
    remediation_code: str | None
    rollback_code: str | None
    code_status: str
    risk_score: float
    created_at: datetime
    updated_at: datetime
    # Denormalised from the linked PolicyRule for convenient display
    rule_title: str | None = None
    rule_short_id: str | None = None


class ProfileRuleCodeUpdate(BaseModel):
    evaluation_code: str | None = None
    remediation_code: str | None = None
    rollback_code: str | None = None


class HITLCommentCreate(BaseModel):
    comment_text: str
    comment_type: str = "review"


class HITLCommentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    profile_rule_id: uuid.UUID
    author_id: uuid.UUID | None
    comment_text: str
    comment_type: str
    created_at: datetime


class CodeGenRequest(BaseModel):
    rule_ids: list[uuid.UUID] | None = None  # None = generate all pending
