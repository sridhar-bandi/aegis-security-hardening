"""Policies router — import and browse security policies."""
from __future__ import annotations

import os
import tempfile
import uuid
from datetime import datetime, timezone
from typing import Annotated

import requests as http_requests
from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aegis.config import settings
from aegis.database import get_db
from aegis.models.policy import Policy, PolicyRule
from aegis.models.user import User
from aegis.schemas.policy import (
    PolicyCodeGenRequest,
    PolicyImportRequest,
    PolicyResponse,
    PolicyRuleCodeUpdate,
    PolicyRuleRejectRequest,
    PolicyRuleResponse,
)
from aegis.services.rbac import check_workspace_access, get_current_user, require_role

router = APIRouter(prefix="/policies", tags=["policies"])

async def _parse_policy_file(file_path: str, fmt: str) -> list:
    if fmt == "OVAL":
        from aegis.services.policy_parser.oval_parser import OVALParser
        return OVALParser().parse(file_path)
    elif fmt == "XCCDF":
        from aegis.services.policy_parser.xccdf_parser import XCCDFParser
        return XCCDFParser().parse(file_path)
    elif fmt == "json":
        from aegis.services.policy_parser.json_parser import JSONPolicyParser
        return JSONPolicyParser().parse(file_path)
    else:
        with open(file_path, encoding="utf-8") as f:
            text = f.read()
        from aegis.services.policy_parser.text_parser import TextPolicyParser
        return await TextPolicyParser().parse(text)


@router.post("/upload", response_model=PolicyResponse, status_code=status.HTTP_201_CREATED)
async def upload_policy(
    workspace_id: uuid.UUID,
    name: str,
    standard: str = Query(default="Custom"),
    fmt: str = Query(default="text", alias="format"),
    file: UploadFile = File(...),
    current_user: Annotated[User, Depends(require_role("admin", "security_officer"))] = None,
    db: Annotated[AsyncSession, Depends(get_db)] = None,
) -> PolicyResponse:
    await check_workspace_access(workspace_id, current_user, db)

    # Save upload to reports dir temporarily
    suffix = os.path.splitext(file.filename or "policy.xml")[1] or ".xml"
    tmp_path = os.path.join(settings.REPORTS_DIR, f"upload_{uuid.uuid4()}{suffix}")
    os.makedirs(settings.REPORTS_DIR, exist_ok=True)
    content = await file.read()
    with open(tmp_path, "wb") as f:
        f.write(content)

    policy_obj = Policy(
        id=uuid.uuid4(),
        workspace_id=workspace_id,
        name=name,
        standard=standard,
        format=fmt,
        file_path=tmp_path,
        created_by=current_user.id,
    )
    db.add(policy_obj)
    await db.flush()

    try:
        rule_data_list = await _parse_policy_file(tmp_path, fmt)
        for rd in rule_data_list:
            rule = PolicyRule(
                id=uuid.uuid4(),
                policy_id=policy_obj.id,
                rule_id=rd.rule_id,
                title=rd.title,
                description=rd.description,
                rationale=rd.rationale,
                severity=rd.severity,
                category=rd.category,
                target_component_types=rd.target_component_types,
                check_content=rd.check_content,
                fix_text=rd.fix_text,
            )
            db.add(rule)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Policy parsing failed: {exc}",
        )

    await db.commit()
    await db.refresh(policy_obj)

    # Auto-trigger development-stage code generation for all imported rules
    from aegis.tasks.codegen_tasks import generate_policy_codes
    generate_policy_codes.delay(str(policy_obj.id))

    return PolicyResponse.model_validate(policy_obj)


@router.get("", response_model=list[PolicyResponse])
async def list_policies(
    workspace_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[PolicyResponse]:
    await check_workspace_access(workspace_id, current_user, db)
    result = await db.execute(
        select(Policy).where(Policy.workspace_id == workspace_id).order_by(Policy.name)
    )
    policies = result.scalars().all()

    # Fetch rule counts and component types — avoid GROUP BY on JSON column
    if policies:
        policy_ids = [p.id for p in policies]
        rules_result = await db.execute(
            select(PolicyRule.policy_id, PolicyRule.target_component_types)
            .where(PolicyRule.policy_id.in_(policy_ids))
        )
        rule_rows = rules_result.all()
        counts: dict = {}
        ctypes: dict = {}
        for row in rule_rows:
            pid = row.policy_id
            counts[pid] = counts.get(pid, 0) + 1
            for ct in (row.target_component_types or []):
                ctypes.setdefault(pid, set()).add(ct)
    else:
        counts, ctypes = {}, {}

    out = []
    for p in policies:
        data = PolicyResponse.model_validate(p)
        data.rule_count = counts.get(p.id, 0)
        data.target_component_types = sorted(ctypes.get(p.id, set()))
        out.append(data)
    return out


@router.get("/{policy_id}/rules", response_model=list[PolicyRuleResponse])
async def list_policy_rules(
    policy_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[PolicyRuleResponse]:
    result = await db.execute(select(Policy).where(Policy.id == policy_id))
    policy = result.scalar_one_or_none()
    if policy is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Policy not found")
    await check_workspace_access(policy.workspace_id, current_user, db)
    rules_result = await db.execute(
        select(PolicyRule).where(PolicyRule.policy_id == policy_id).order_by(PolicyRule.severity)
    )
    return [PolicyRuleResponse.model_validate(r) for r in rules_result.scalars().all()]


@router.post("/{policy_id}/generate-codes", status_code=status.HTTP_202_ACCEPTED)
async def trigger_policy_code_generation(
    policy_id: uuid.UUID,
    body: PolicyCodeGenRequest,
    current_user: Annotated[User, Depends(require_role("admin", "security_officer"))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    """
    Development stage: trigger LLM code generation for every rule in a policy.
    Generated code (evaluate / remediate / rollback) is stored on each PolicyRule
    and upserted into the Milvus contextual data store for retrieval during enforcement.
    """
    result = await db.execute(select(Policy).where(Policy.id == policy_id))
    policy = result.scalar_one_or_none()
    if policy is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Policy not found")
    await check_workspace_access(policy.workspace_id, current_user, db)

    from aegis.tasks.codegen_tasks import generate_policy_codes
    str_rule_ids = [str(r) for r in body.rule_ids] if body.rule_ids else None
    task = generate_policy_codes.delay(str(policy_id), str_rule_ids)
    return {
        "task_id": task.id,
        "status": "accepted",
        "policy_id": str(policy_id),
        "channel": f"ws:codegen:policy:{policy_id}",
    }


@router.delete("/{policy_id}", status_code=status.HTTP_204_NO_CONTENT, response_model=None)
async def delete_policy(
    policy_id: uuid.UUID,
    current_user: Annotated[User, Depends(require_role("admin", "security_officer"))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> None:
    result = await db.execute(select(Policy).where(Policy.id == policy_id))
    policy = result.scalar_one_or_none()
    if policy is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Policy not found")
    await check_workspace_access(policy.workspace_id, current_user, db)
    await db.delete(policy)
    await db.commit()


# --- Rule Review Endpoints ---


async def _get_policy_rule(policy_id: uuid.UUID, rule_id: uuid.UUID, db: AsyncSession, current_user: User) -> PolicyRule:
    """Helper: fetch a PolicyRule ensuring workspace access."""
    result = await db.execute(select(Policy).where(Policy.id == policy_id))
    policy = result.scalar_one_or_none()
    if policy is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Policy not found")
    await check_workspace_access(policy.workspace_id, current_user, db)
    result = await db.execute(
        select(PolicyRule).where(PolicyRule.id == rule_id, PolicyRule.policy_id == policy_id)
    )
    rule = result.scalar_one_or_none()
    if rule is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Rule not found")
    return rule


@router.patch("/{policy_id}/rules/{rule_id}/code", response_model=PolicyRuleResponse)
async def update_rule_code(
    policy_id: uuid.UUID,
    rule_id: uuid.UUID,
    body: PolicyRuleCodeUpdate,
    current_user: Annotated[User, Depends(require_role("admin", "security_officer"))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> PolicyRuleResponse:
    """Manually update rule implementation code."""
    rule = await _get_policy_rule(policy_id, rule_id, db, current_user)
    if body.evaluation_code is not None:
        rule.evaluation_code = body.evaluation_code
    if body.remediation_code is not None:
        rule.remediation_code = body.remediation_code
    if body.rollback_code is not None:
        rule.rollback_code = body.rollback_code
    rule.code_source = "manual"
    rule.code_status = "reviewed"
    await db.commit()
    await db.refresh(rule)
    return PolicyRuleResponse.model_validate(rule)


@router.post("/{policy_id}/rules/{rule_id}/approve", response_model=PolicyRuleResponse)
async def approve_rule(
    policy_id: uuid.UUID,
    rule_id: uuid.UUID,
    current_user: Annotated[User, Depends(require_role("admin", "security_officer"))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> PolicyRuleResponse:
    """Approve a rule's implementation code."""
    rule = await _get_policy_rule(policy_id, rule_id, db, current_user)
    if not rule.evaluation_code:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Rule must have evaluation_code before approval",
        )
    rule.code_status = "approved"
    rule.reviewed_by = current_user.id
    rule.reviewed_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(rule)
    return PolicyRuleResponse.model_validate(rule)


@router.post("/{policy_id}/rules/{rule_id}/reject", response_model=PolicyRuleResponse)
async def reject_rule(
    policy_id: uuid.UUID,
    rule_id: uuid.UUID,
    body: PolicyRuleRejectRequest | None = None,
    current_user: Annotated[User, Depends(require_role("admin", "security_officer"))] = None,
    db: Annotated[AsyncSession, Depends(get_db)] = None,
) -> PolicyRuleResponse:
    """Reject a rule's implementation code."""
    rule = await _get_policy_rule(policy_id, rule_id, db, current_user)
    rule.code_status = "rejected"
    rule.reviewed_by = current_user.id
    rule.reviewed_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(rule)
    return PolicyRuleResponse.model_validate(rule)


@router.post("/{policy_id}/rules/{rule_id}/import", response_model=PolicyRuleResponse)
async def import_rule_code(
    policy_id: uuid.UUID,
    rule_id: uuid.UUID,
    code_type: str = Query(..., description="evaluation | remediation | rollback"),
    file: UploadFile = File(...),
    current_user: Annotated[User, Depends(require_role("admin", "security_officer"))] = None,
    db: Annotated[AsyncSession, Depends(get_db)] = None,
) -> PolicyRuleResponse:
    """Import an external script file as rule implementation code."""
    if code_type not in ("evaluation", "remediation", "rollback"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="code_type must be one of: evaluation, remediation, rollback",
        )
    rule = await _get_policy_rule(policy_id, rule_id, db, current_user)
    content = (await file.read()).decode("utf-8")
    setattr(rule, f"{code_type}_code", content)
    rule.code_source = "imported"
    rule.imported_filename = file.filename
    rule.code_status = "reviewed"
    await db.commit()
    await db.refresh(rule)
    return PolicyRuleResponse.model_validate(rule)
