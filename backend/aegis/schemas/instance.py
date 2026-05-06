"""Solution instance and enforcement schemas."""
from __future__ import annotations
import uuid
from datetime import datetime
from typing import Any
from pydantic import BaseModel, ConfigDict


class SolutionInstanceCreate(BaseModel):
    workspace_id: uuid.UUID
    name: str
    solution_type_id: uuid.UUID | None = None
    blueprint_id: uuid.UUID | None = None
    scid_json: dict[str, Any] | None = None
    scid_filename: str | None = None


class SolutionInstanceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    workspace_id: uuid.UUID
    name: str
    solution_type_id: uuid.UUID | None
    blueprint_id: uuid.UUID | None
    owner_id: uuid.UUID
    created_at: datetime
    scid_json: dict[str, Any] | None = None
    scid_filename: str | None = None


class EnforcementRequest(BaseModel):
    rule_ids: list[uuid.UUID] | None = None  # None = all approved rules
    blueprint_id: uuid.UUID | None = None  # override if not set on instance


class EnforcementJobResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    instance_id: uuid.UUID
    job_type: str
    status: str
    celery_task_id: str | None
    result_summary: dict[str, Any] | None
    created_at: datetime
    completed_at: datetime | None


class ComplianceReportResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    instance_id: uuid.UUID
    job_id: uuid.UUID | None
    report_type: str
    file_path: str | None
    summary: dict[str, Any] | None
    created_at: datetime


class ChannelRisk(BaseModel):
    source: str
    target: str
    protocol: str
    tls_versions: list[str]
    cipher_suites: list[str]
    port: int
    risk_score: float


class ImpactAssessmentReport(BaseModel):
    instance_id: str
    communication_channels: list[ChannelRisk]
    generated_at: datetime


class DryRunRuleResult(BaseModel):
    rule_id: str
    blueprint_rule_id: str
    title: str
    risk_score: float
    impacted_channels: list[ChannelRisk]
    break_risk: str  # "none" | "low" | "medium" | "high" | "critical"
    explanation: str


class DryRunReport(BaseModel):
    instance_id: str
    safe_rules: list[DryRunRuleResult]
    risky_rules: list[DryRunRuleResult]
    breaking_rules: list[DryRunRuleResult]
    generated_at: datetime
