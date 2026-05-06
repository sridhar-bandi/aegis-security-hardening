"""Hardening Blueprints router — HITL review, code gen trigger."""
from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aegis.database import get_db
from aegis.models.hardening_blueprint import HardeningBlueprint, HITLComment, BlueprintRule
from aegis.models.policy import PolicyRule
from aegis.models.policy_profile import PolicyProfile
from aegis.models.solution_type import SolutionType
from aegis.models.user import User
from aegis.schemas.blueprint import (
    CodeGenRequest,
    HardeningBlueprintCreate,
    HardeningBlueprintResponse,
    HITLCommentCreate,
    HITLCommentResponse,
    BlueprintRuleCodeUpdate,
    BlueprintRuleResponse,
)
from aegis.services.rbac import check_workspace_access, get_current_user, require_role

router = APIRouter(prefix="/blueprints", tags=["blueprints"])


@router.get("", response_model=list[HardeningBlueprintResponse])
async def list_blueprints(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    solution_type_id: uuid.UUID | None = None,
    workspace_id: uuid.UUID | None = None,
) -> list[HardeningBlueprintResponse]:
    """List hardening blueprints filtered by solution_type_id or workspace_id."""
    if solution_type_id is not None:
        st_result = await db.execute(select(SolutionType).where(SolutionType.id == solution_type_id))
        st = st_result.scalar_one_or_none()
        if st is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="SolutionType not found")
        await check_workspace_access(st.workspace_id, current_user, db)
        result = await db.execute(
            select(HardeningBlueprint)
            .where(HardeningBlueprint.solution_type_id == solution_type_id)
            .order_by(HardeningBlueprint.name)
        )
    elif workspace_id is not None:
        await check_workspace_access(workspace_id, current_user, db)
        result = await db.execute(
            select(HardeningBlueprint)
            .join(SolutionType, HardeningBlueprint.solution_type_id == SolutionType.id)
            .where(SolutionType.workspace_id == workspace_id)
            .order_by(HardeningBlueprint.name)
        )
    else:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Provide solution_type_id or workspace_id")
    return [HardeningBlueprintResponse.model_validate(p) for p in result.scalars().all()]


@router.post("", response_model=HardeningBlueprintResponse, status_code=status.HTTP_201_CREATED)
async def create_blueprint(
    body: HardeningBlueprintCreate,
    current_user: Annotated[User, Depends(require_role("admin", "security_officer"))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> HardeningBlueprintResponse:
    # Verify SolutionType exists and user has access
    st_result = await db.execute(select(SolutionType).where(SolutionType.id == body.solution_type_id))
    st = st_result.scalar_one_or_none()
    if st is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="SolutionType not found")
    await check_workspace_access(st.workspace_id, current_user, db)

    # Validate that every component in the solution type has a profile assigned
    components = st.component_selection or []
    missing = [c for c in components if c not in body.component_profile_map]
    if missing:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"No profile mapped for component(s): {', '.join(missing)}",
        )

    # Validate all profiles are locked
    profile_ids = list(body.component_profile_map.values())
    profiles_result = await db.execute(
        select(PolicyProfile).where(PolicyProfile.id.in_(profile_ids))
    )
    profiles = {p.id: p for p in profiles_result.scalars().all()}
    not_locked = [str(pid) for pid in profile_ids if pid not in profiles or profiles[pid].status != "locked"]
    if not_locked:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Profile(s) not found or not locked: {', '.join(not_locked)}",
        )

    # Serialize map: UUID values → str for JSON storage
    cpm_serialized = {k: str(v) for k, v in body.component_profile_map.items()}

    blueprint = HardeningBlueprint(
        id=uuid.uuid4(),
        name=body.name,
        solution_type_id=body.solution_type_id,
        component_profile_map=cpm_serialized,
        created_by=current_user.id,
    )
    db.add(blueprint)
    await db.flush()

    # Create BlueprintRules from each profile's PolicyRules
    if components:
        for component_id in components:
            profile_id = body.component_profile_map[component_id]
            profile = profiles[profile_id]

            # Resolve rules: included_rule_ids for tailored, all policy rules for standard
            if profile.included_rule_ids:
                rule_ids = [uuid.UUID(rid) for rid in profile.included_rule_ids]
                rules_result = await db.execute(
                    select(PolicyRule).where(PolicyRule.id.in_(rule_ids))
                )
            else:
                rules_result = await db.execute(
                    select(PolicyRule).where(PolicyRule.policy_id == profile.policy_id)
                )
            policy_rules = rules_result.scalars().all()
            for pr in policy_rules:
                db.add(BlueprintRule(
                    id=uuid.uuid4(),
                    blueprint_id=blueprint.id,
                    policy_rule_id=pr.id,
                    component_type=component_id,
                    evaluation_code=pr.evaluation_code,
                    remediation_code=pr.remediation_code,
                    rollback_code=pr.rollback_code,
                    code_status="approved",
                    risk_score=5.0,
                ))

    await db.commit()
    await db.refresh(blueprint)
    return HardeningBlueprintResponse.model_validate(blueprint)


@router.get("/{blueprint_id}", response_model=HardeningBlueprintResponse)
async def get_blueprint(
    blueprint_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> HardeningBlueprintResponse:
    result = await db.execute(select(HardeningBlueprint).where(HardeningBlueprint.id == blueprint_id))
    blueprint = result.scalar_one_or_none()
    if blueprint is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Blueprint not found")
    st_result = await db.execute(select(SolutionType).where(SolutionType.id == blueprint.solution_type_id))
    st = st_result.scalar_one_or_none()
    if st:
        await check_workspace_access(st.workspace_id, current_user, db)
    return HardeningBlueprintResponse.model_validate(blueprint)


@router.get("/{blueprint_id}/rules", response_model=list[BlueprintRuleResponse])
async def list_blueprint_rules(
    blueprint_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[BlueprintRuleResponse]:
    from sqlalchemy.orm import selectinload
    result = await db.execute(
        select(BlueprintRule)
        .options(selectinload(BlueprintRule.policy_rule))
        .where(BlueprintRule.blueprint_id == blueprint_id)
        .order_by(BlueprintRule.component_type, BlueprintRule.created_at)
    )
    rows = result.scalars().all()
    out = []
    for r in rows:
        data = BlueprintRuleResponse.model_validate(r)
        if r.policy_rule is not None:
            data.rule_title = r.policy_rule.title
            data.rule_short_id = r.policy_rule.rule_id
        out.append(data)
    return out


@router.patch("/{blueprint_id}/rules/{rule_id}/code", response_model=BlueprintRuleResponse)
async def update_rule_code(
    blueprint_id: uuid.UUID,
    rule_id: uuid.UUID,
    body: BlueprintRuleCodeUpdate,
    current_user: Annotated[User, Depends(require_role("admin", "security_officer"))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> BlueprintRuleResponse:
    result = await db.execute(
        select(BlueprintRule).where(BlueprintRule.id == rule_id, BlueprintRule.blueprint_id == blueprint_id)
    )
    pr = result.scalar_one_or_none()
    if pr is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="BlueprintRule not found")
    if body.evaluation_code is not None:
        pr.evaluation_code = body.evaluation_code
    if body.remediation_code is not None:
        pr.remediation_code = body.remediation_code
    if body.rollback_code is not None:
        pr.rollback_code = body.rollback_code
    pr.code_status = "reviewed"
    await db.commit()
    await db.refresh(pr)
    return BlueprintRuleResponse.model_validate(pr)


@router.post("/{blueprint_id}/rules/{rule_id}/approve", response_model=BlueprintRuleResponse)
async def approve_rule(
    blueprint_id: uuid.UUID,
    rule_id: uuid.UUID,
    current_user: Annotated[User, Depends(require_role("admin", "security_officer"))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> BlueprintRuleResponse:
    result = await db.execute(
        select(BlueprintRule).where(BlueprintRule.id == rule_id, BlueprintRule.blueprint_id == blueprint_id)
    )
    pr = result.scalar_one_or_none()
    if pr is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="BlueprintRule not found")
    pr.code_status = "approved"
    await db.commit()
    await db.refresh(pr)
    return BlueprintRuleResponse.model_validate(pr)


@router.post("/{blueprint_id}/rules/{rule_id}/reject", response_model=BlueprintRuleResponse)
async def reject_rule(
    blueprint_id: uuid.UUID,
    rule_id: uuid.UUID,
    current_user: Annotated[User, Depends(require_role("admin", "security_officer"))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> BlueprintRuleResponse:
    result = await db.execute(
        select(BlueprintRule).where(BlueprintRule.id == rule_id, BlueprintRule.blueprint_id == blueprint_id)
    )
    pr = result.scalar_one_or_none()
    if pr is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="BlueprintRule not found")
    pr.code_status = "rejected"
    await db.commit()
    await db.refresh(pr)
    return BlueprintRuleResponse.model_validate(pr)


@router.post("/{blueprint_id}/rules/{rule_id}/comments", response_model=HITLCommentResponse, status_code=status.HTTP_201_CREATED)
async def add_comment(
    blueprint_id: uuid.UUID,
    rule_id: uuid.UUID,
    body: HITLCommentCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> HITLCommentResponse:
    result = await db.execute(
        select(BlueprintRule).where(BlueprintRule.id == rule_id, BlueprintRule.blueprint_id == blueprint_id)
    )
    if result.scalar_one_or_none() is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="BlueprintRule not found")
    comment = HITLComment(
        id=uuid.uuid4(),
        blueprint_rule_id=rule_id,
        author_id=current_user.id,
        comment_text=body.comment_text,
        comment_type=body.comment_type,
    )
    db.add(comment)
    await db.commit()
    await db.refresh(comment)
    return HITLCommentResponse.model_validate(comment)


@router.post("/{blueprint_id}/generate-codes", status_code=status.HTTP_202_ACCEPTED)
async def trigger_code_generation(
    blueprint_id: uuid.UUID,
    body: CodeGenRequest,
    current_user: Annotated[User, Depends(require_role("admin", "security_officer"))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    from aegis.tasks.codegen_tasks import generate_blueprint_codes
    rule_ids = [str(r) for r in body.rule_ids] if body.rule_ids else None
    task = generate_blueprint_codes.delay(str(blueprint_id), rule_ids)
    return {"task_id": task.id, "status": "accepted", "blueprint_id": str(blueprint_id)}


@router.delete("/{blueprint_id}", status_code=status.HTTP_204_NO_CONTENT, response_model=None)
async def delete_blueprint(
    blueprint_id: uuid.UUID,
    current_user: Annotated[User, Depends(require_role("admin", "security_officer"))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> None:
    result = await db.execute(select(HardeningBlueprint).where(HardeningBlueprint.id == blueprint_id))
    blueprint = result.scalar_one_or_none()
    if blueprint is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Blueprint not found")
    st_result = await db.execute(select(SolutionType).where(SolutionType.id == blueprint.solution_type_id))
    st = st_result.scalar_one_or_none()
    if st:
        await check_workspace_access(st.workspace_id, current_user, db)
    await db.delete(blueprint)
    await db.commit()
