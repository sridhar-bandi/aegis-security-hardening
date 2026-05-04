"""Hardening Profiles router — HITL review, code gen trigger."""
from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aegis.database import get_db
from aegis.models.hardening_profile import HardeningProfile, HITLComment, ProfileRule
from aegis.models.policy import PolicyRule
from aegis.models.solution_type import SolutionType
from aegis.models.user import User
from aegis.schemas.profile import (
    CodeGenRequest,
    HardeningProfileCreate,
    HardeningProfileResponse,
    HITLCommentCreate,
    HITLCommentResponse,
    ProfileRuleCodeUpdate,
    ProfileRuleResponse,
)
from aegis.services.rbac import check_workspace_access, get_current_user, require_role

router = APIRouter(prefix="/profiles", tags=["profiles"])


@router.post("", response_model=HardeningProfileResponse, status_code=status.HTTP_201_CREATED)
async def create_profile(
    body: HardeningProfileCreate,
    current_user: Annotated[User, Depends(require_role("admin", "security_officer"))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> HardeningProfileResponse:
    # Verify SolutionType exists and user has access
    st_result = await db.execute(select(SolutionType).where(SolutionType.id == body.solution_type_id))
    st = st_result.scalar_one_or_none()
    if st is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="SolutionType not found")
    await check_workspace_access(st.workspace_id, current_user, db)

    profile = HardeningProfile(
        id=uuid.uuid4(),
        name=body.name,
        solution_type_id=body.solution_type_id,
        policy_id=body.policy_id,
        created_by=current_user.id,
    )
    db.add(profile)
    await db.flush()

    # Create ProfileRules for each selected component × policy rule
    if st.component_selection:
        rules_result = await db.execute(
            select(PolicyRule).where(PolicyRule.policy_id == body.policy_id)
        )
        policy_rules = rules_result.scalars().all()
        for component_id in st.component_selection:
            for pr in policy_rules:
                db.add(ProfileRule(
                    id=uuid.uuid4(),
                    profile_id=profile.id,
                    policy_rule_id=pr.id,
                    component_type=component_id,
                    code_status="pending",
                    risk_score=5.0,
                ))

    await db.commit()
    await db.refresh(profile)
    return HardeningProfileResponse.model_validate(profile)


@router.get("/{profile_id}", response_model=HardeningProfileResponse)
async def get_profile(
    profile_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> HardeningProfileResponse:
    result = await db.execute(select(HardeningProfile).where(HardeningProfile.id == profile_id))
    profile = result.scalar_one_or_none()
    if profile is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found")
    st_result = await db.execute(select(SolutionType).where(SolutionType.id == profile.solution_type_id))
    st = st_result.scalar_one_or_none()
    if st:
        await check_workspace_access(st.workspace_id, current_user, db)
    return HardeningProfileResponse.model_validate(profile)


@router.get("/{profile_id}/rules", response_model=list[ProfileRuleResponse])
async def list_profile_rules(
    profile_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[ProfileRuleResponse]:
    result = await db.execute(
        select(ProfileRule).where(ProfileRule.profile_id == profile_id).order_by(ProfileRule.code_status)
    )
    return [ProfileRuleResponse.model_validate(r) for r in result.scalars().all()]


@router.patch("/{profile_id}/rules/{rule_id}/code", response_model=ProfileRuleResponse)
async def update_rule_code(
    profile_id: uuid.UUID,
    rule_id: uuid.UUID,
    body: ProfileRuleCodeUpdate,
    current_user: Annotated[User, Depends(require_role("admin", "security_officer"))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ProfileRuleResponse:
    result = await db.execute(
        select(ProfileRule).where(ProfileRule.id == rule_id, ProfileRule.profile_id == profile_id)
    )
    pr = result.scalar_one_or_none()
    if pr is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="ProfileRule not found")
    if body.evaluation_code is not None:
        pr.evaluation_code = body.evaluation_code
    if body.remediation_code is not None:
        pr.remediation_code = body.remediation_code
    if body.rollback_code is not None:
        pr.rollback_code = body.rollback_code
    pr.code_status = "reviewed"
    await db.commit()
    await db.refresh(pr)
    return ProfileRuleResponse.model_validate(pr)


@router.post("/{profile_id}/rules/{rule_id}/approve", response_model=ProfileRuleResponse)
async def approve_rule(
    profile_id: uuid.UUID,
    rule_id: uuid.UUID,
    current_user: Annotated[User, Depends(require_role("admin", "security_officer"))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ProfileRuleResponse:
    result = await db.execute(
        select(ProfileRule).where(ProfileRule.id == rule_id, ProfileRule.profile_id == profile_id)
    )
    pr = result.scalar_one_or_none()
    if pr is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="ProfileRule not found")
    pr.code_status = "approved"
    await db.commit()
    await db.refresh(pr)
    return ProfileRuleResponse.model_validate(pr)


@router.post("/{profile_id}/rules/{rule_id}/reject", response_model=ProfileRuleResponse)
async def reject_rule(
    profile_id: uuid.UUID,
    rule_id: uuid.UUID,
    current_user: Annotated[User, Depends(require_role("admin", "security_officer"))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ProfileRuleResponse:
    result = await db.execute(
        select(ProfileRule).where(ProfileRule.id == rule_id, ProfileRule.profile_id == profile_id)
    )
    pr = result.scalar_one_or_none()
    if pr is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="ProfileRule not found")
    pr.code_status = "rejected"
    await db.commit()
    await db.refresh(pr)
    return ProfileRuleResponse.model_validate(pr)


@router.post("/{profile_id}/rules/{rule_id}/comments", response_model=HITLCommentResponse, status_code=status.HTTP_201_CREATED)
async def add_comment(
    profile_id: uuid.UUID,
    rule_id: uuid.UUID,
    body: HITLCommentCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> HITLCommentResponse:
    result = await db.execute(
        select(ProfileRule).where(ProfileRule.id == rule_id, ProfileRule.profile_id == profile_id)
    )
    if result.scalar_one_or_none() is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="ProfileRule not found")
    comment = HITLComment(
        id=uuid.uuid4(),
        profile_rule_id=rule_id,
        author_id=current_user.id,
        comment_text=body.comment_text,
        comment_type=body.comment_type,
    )
    db.add(comment)
    await db.commit()
    await db.refresh(comment)
    return HITLCommentResponse.model_validate(comment)


@router.post("/{profile_id}/generate-codes", status_code=status.HTTP_202_ACCEPTED)
async def trigger_code_generation(
    profile_id: uuid.UUID,
    body: CodeGenRequest,
    current_user: Annotated[User, Depends(require_role("admin", "security_officer"))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    from aegis.tasks.codegen_tasks import generate_profile_codes
    rule_ids = [str(r) for r in body.rule_ids] if body.rule_ids else None
    task = generate_profile_codes.delay(str(profile_id), rule_ids)
    return {"task_id": task.id, "status": "accepted", "profile_id": str(profile_id)}


@router.delete("/{profile_id}", status_code=status.HTTP_204_NO_CONTENT, response_model=None)
async def delete_profile(
    profile_id: uuid.UUID,
    current_user: Annotated[User, Depends(require_role("admin", "security_officer"))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> None:
    result = await db.execute(select(HardeningProfile).where(HardeningProfile.id == profile_id))
    profile = result.scalar_one_or_none()
    if profile is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found")
    st_result = await db.execute(select(SolutionType).where(SolutionType.id == profile.solution_type_id))
    st = st_result.scalar_one_or_none()
    if st:
        await check_workspace_access(st.workspace_id, current_user, db)
    await db.delete(profile)
    await db.commit()
