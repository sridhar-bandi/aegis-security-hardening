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


@router.get("", response_model=list[HardeningProfileResponse])
async def list_profiles(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    solution_type_id: uuid.UUID | None = None,
    workspace_id: uuid.UUID | None = None,
) -> list[HardeningProfileResponse]:
    """List hardening profiles filtered by solution_type_id or workspace_id."""
    if solution_type_id is not None:
        st_result = await db.execute(select(SolutionType).where(SolutionType.id == solution_type_id))
        st = st_result.scalar_one_or_none()
        if st is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="SolutionType not found")
        await check_workspace_access(st.workspace_id, current_user, db)
        result = await db.execute(
            select(HardeningProfile)
            .where(HardeningProfile.solution_type_id == solution_type_id)
            .order_by(HardeningProfile.name)
        )
    elif workspace_id is not None:
        await check_workspace_access(workspace_id, current_user, db)
        result = await db.execute(
            select(HardeningProfile)
            .join(SolutionType, HardeningProfile.solution_type_id == SolutionType.id)
            .where(SolutionType.workspace_id == workspace_id)
            .order_by(HardeningProfile.name)
        )
    else:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Provide solution_type_id or workspace_id")
    return [HardeningProfileResponse.model_validate(p) for p in result.scalars().all()]


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

    # Validate that every component in the solution type has a policy assigned
    components = st.component_selection or []
    missing = [c for c in components if c not in body.component_policy_map]
    if missing:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"No policy mapped for component(s): {', '.join(missing)}",
        )

    # Serialize map: UUID values → str for JSON storage
    cpm_serialized = {k: str(v) for k, v in body.component_policy_map.items()}

    profile = HardeningProfile(
        id=uuid.uuid4(),
        name=body.name,
        solution_type_id=body.solution_type_id,
        component_policy_map=cpm_serialized,
        created_by=current_user.id,
    )
    db.add(profile)
    await db.flush()

    # Create ProfileRules: for each component, use its mapped policy's rules
    if components:
        for component_id in components:
            policy_id = body.component_policy_map[component_id]
            rules_result = await db.execute(
                select(PolicyRule).where(PolicyRule.policy_id == policy_id)
            )
            policy_rules = rules_result.scalars().all()
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
    from sqlalchemy.orm import selectinload
    result = await db.execute(
        select(ProfileRule)
        .options(selectinload(ProfileRule.policy_rule))
        .where(ProfileRule.profile_id == profile_id)
        .order_by(ProfileRule.component_type, ProfileRule.created_at)
    )
    rows = result.scalars().all()
    out = []
    for r in rows:
        data = ProfileRuleResponse.model_validate(r)
        if r.policy_rule is not None:
            data.rule_title = r.policy_rule.title
            data.rule_short_id = r.policy_rule.rule_id
        out.append(data)
    return out


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
