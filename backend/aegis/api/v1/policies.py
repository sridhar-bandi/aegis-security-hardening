"""Policies router — import and browse security policies."""
from __future__ import annotations

import os
import tempfile
import uuid
from typing import Annotated

import requests as http_requests
from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aegis.config import settings
from aegis.database import get_db
from aegis.models.policy import Policy, PolicyRule
from aegis.models.user import User
from aegis.schemas.policy import PolicyImportRequest, PolicyResponse, PolicyRuleResponse
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
    return [PolicyResponse.model_validate(p) for p in result.scalars().all()]


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
