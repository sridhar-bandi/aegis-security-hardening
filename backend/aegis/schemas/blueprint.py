"""Hardening blueprint schemas."""
from __future__ import annotations
import uuid
from datetime import datetime
from pydantic import BaseModel, ConfigDict


class HardeningBlueprintCreate(BaseModel):
    name: str
    solution_type_id: uuid.UUID
    # Maps each component_type (string) to the locked profile_id (UUID) that governs it.
    # e.g. {"server": "<profile-uuid>", "network_switch": "<profile-uuid>"}
    component_profile_map: dict[str, uuid.UUID]


class HardeningBlueprintResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    solution_type_id: uuid.UUID
    component_profile_map: dict | None
    status: str
    created_at: datetime


class BlueprintRuleResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    blueprint_id: uuid.UUID
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


class BlueprintRuleCodeUpdate(BaseModel):
    evaluation_code: str | None = None
    remediation_code: str | None = None
    rollback_code: str | None = None


class HITLCommentCreate(BaseModel):
    comment_text: str
    comment_type: str = "review"


class HITLCommentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    blueprint_rule_id: uuid.UUID
    author_id: uuid.UUID | None
    comment_text: str
    comment_type: str
    created_at: datetime


class CodeGenRequest(BaseModel):
    rule_ids: list[uuid.UUID] | None = None  # None = generate all pending
