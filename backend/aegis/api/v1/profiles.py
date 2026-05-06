"""Profiles router — CRUD and lifecycle for policy profiles."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aegis.database import get_db
from aegis.models.policy import Policy, PolicyRule
from aegis.models.policy_profile import PolicyProfile
from aegis.models.user import User
from aegis.schemas.profile import PolicyProfileCreate, PolicyProfileResponse, PolicyProfileUpdate
from aegis.services.rbac import check_workspace_access, get_current_user, require_role

router = APIRouter(prefix="/profiles", tags=["profiles"])


# --- Helper ---

async def _compute_profile_counts(profile: PolicyProfile, db: AsyncSession) -> tuple[int, int]:
    """Compute (rule_count, approved_count) for a profile."""
    if profile.included_rule_ids:
        rule_ids = [uuid.UUID(rid) for rid in profile.included_rule_ids]
        result = await db.execute(
            select(PolicyRule.id, PolicyRule.code_status).where(PolicyRule.id.in_(rule_ids))
        )
    else:
        # Standard profile — all rules in the policy
        result = await db.execute(
            select(PolicyRule.id, PolicyRule.code_status).where(PolicyRule.policy_id == profile.policy_id)
        )
    rows = result.all()
    rule_count = len(rows)
    approved_count = sum(1 for r in rows if r.code_status == "approved")
    return rule_count, approved_count


def _profile_response(profile: PolicyProfile, rule_count: int, approved_count: int) -> PolicyProfileResponse:
    data = PolicyProfileResponse.model_validate(profile)
    data.rule_count = rule_count
    data.approved_count = approved_count
    return data


# --- Workspace-level endpoints ---


@router.get("/workspace/{workspace_id}", response_model=list[PolicyProfileResponse])
async def list_workspace_profiles(
    workspace_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    status_filter: str | None = None,
) -> list[PolicyProfileResponse]:
    """List profiles in a workspace, optionally filtered by status."""
    await check_workspace_access(workspace_id, current_user, db)
    query = select(PolicyProfile).where(PolicyProfile.workspace_id == workspace_id)
    if status_filter:
        query = query.where(PolicyProfile.status == status_filter)
    query = query.order_by(PolicyProfile.name)
    profiles_result = await db.execute(query)
    profiles = profiles_result.scalars().all()
    out = []
    for p in profiles:
        rule_count, approved_count = await _compute_profile_counts(p, db)
        out.append(_profile_response(p, rule_count, approved_count))
    return out


# --- Policy-scoped endpoints (create / list) ---


@router.post("/policies/{policy_id}/profiles", response_model=PolicyProfileResponse, status_code=status.HTTP_201_CREATED)
async def create_profile(
    policy_id: uuid.UUID,
    body: PolicyProfileCreate,
    current_user: Annotated[User, Depends(require_role("admin", "security_officer"))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> PolicyProfileResponse:
    """Create a new policy profile (standard or tailored)."""
    result = await db.execute(select(Policy).where(Policy.id == policy_id))
    policy = result.scalar_one_or_none()
    if policy is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Policy not found")
    await check_workspace_access(policy.workspace_id, current_user, db)

    included_rule_ids = None
    if body.profile_type == "tailored":
        if not body.included_rule_ids:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Tailored profiles require included_rule_ids",
            )
        # Validate all rule IDs belong to this policy
        rule_result = await db.execute(
            select(PolicyRule.id).where(
                PolicyRule.policy_id == policy_id,
                PolicyRule.id.in_(body.included_rule_ids),
            )
        )
        found_ids = {r.id for r in rule_result.all()}
        missing = set(body.included_rule_ids) - found_ids
        if missing:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Rule IDs not found in policy: {[str(m) for m in missing]}",
            )
        included_rule_ids = [str(rid) for rid in body.included_rule_ids]

    profile = PolicyProfile(
        id=uuid.uuid4(),
        policy_id=policy_id,
        workspace_id=policy.workspace_id,
        name=body.name,
        description=body.description,
        profile_type=body.profile_type,
        included_rule_ids=included_rule_ids,
        created_by=current_user.id,
    )
    db.add(profile)
    await db.commit()
    await db.refresh(profile)
    rule_count, approved_count = await _compute_profile_counts(profile, db)
    return _profile_response(profile, rule_count, approved_count)


@router.get("/policies/{policy_id}/profiles", response_model=list[PolicyProfileResponse])
async def list_profiles(
    policy_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[PolicyProfileResponse]:
    """List all profiles for a policy."""
    result = await db.execute(select(Policy).where(Policy.id == policy_id))
    policy = result.scalar_one_or_none()
    if policy is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Policy not found")
    await check_workspace_access(policy.workspace_id, current_user, db)

    profiles_result = await db.execute(
        select(PolicyProfile).where(PolicyProfile.policy_id == policy_id).order_by(PolicyProfile.name)
    )
    profiles = profiles_result.scalars().all()
    out = []
    for p in profiles:
        rule_count, approved_count = await _compute_profile_counts(p, db)
        out.append(_profile_response(p, rule_count, approved_count))
    return out


# --- Profile-specific endpoints ---


@router.get("/{profile_id}", response_model=PolicyProfileResponse)
async def get_profile(
    profile_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> PolicyProfileResponse:
    """Get a single profile by ID."""
    result = await db.execute(select(PolicyProfile).where(PolicyProfile.id == profile_id))
    profile = result.scalar_one_or_none()
    if profile is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found")
    await check_workspace_access(profile.workspace_id, current_user, db)
    rule_count, approved_count = await _compute_profile_counts(profile, db)
    return _profile_response(profile, rule_count, approved_count)


@router.patch("/{profile_id}", response_model=PolicyProfileResponse)
async def update_profile(
    profile_id: uuid.UUID,
    body: PolicyProfileUpdate,
    current_user: Annotated[User, Depends(require_role("admin", "security_officer"))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> PolicyProfileResponse:
    """Update a draft profile."""
    result = await db.execute(select(PolicyProfile).where(PolicyProfile.id == profile_id))
    profile = result.scalar_one_or_none()
    if profile is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found")
    await check_workspace_access(profile.workspace_id, current_user, db)
    if profile.status != "draft":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Only draft profiles can be modified")
    if body.name is not None:
        profile.name = body.name
    if body.description is not None:
        profile.description = body.description
    if body.included_rule_ids is not None:
        # Validate rule IDs
        rule_result = await db.execute(
            select(PolicyRule.id).where(
                PolicyRule.policy_id == profile.policy_id,
                PolicyRule.id.in_(body.included_rule_ids),
            )
        )
        found_ids = {r.id for r in rule_result.all()}
        missing = set(body.included_rule_ids) - found_ids
        if missing:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Rule IDs not found in policy: {[str(m) for m in missing]}",
            )
        profile.included_rule_ids = [str(rid) for rid in body.included_rule_ids]
    await db.commit()
    await db.refresh(profile)
    rule_count, approved_count = await _compute_profile_counts(profile, db)
    return _profile_response(profile, rule_count, approved_count)


@router.delete("/{profile_id}", status_code=status.HTTP_204_NO_CONTENT, response_class=Response)
async def delete_profile(
    profile_id: uuid.UUID,
    current_user: Annotated[User, Depends(require_role("admin", "security_officer"))],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Delete a profile (draft or locked)."""
    result = await db.execute(select(PolicyProfile).where(PolicyProfile.id == profile_id))
    profile = result.scalar_one_or_none()
    if profile is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found")
    await check_workspace_access(profile.workspace_id, current_user, db)
    if profile.status not in ("draft", "locked"):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Only draft or locked profiles can be deleted")
    await db.delete(profile)
    await db.commit()


@router.post("/{profile_id}/promote", response_model=PolicyProfileResponse)
async def promote_profile(
    profile_id: uuid.UUID,
    current_user: Annotated[User, Depends(require_role("admin", "security_officer"))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> PolicyProfileResponse:
    """Lock a profile — all included rules must be approved."""
    result = await db.execute(select(PolicyProfile).where(PolicyProfile.id == profile_id))
    profile = result.scalar_one_or_none()
    if profile is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found")
    await check_workspace_access(profile.workspace_id, current_user, db)
    if profile.status == "locked":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Profile is already locked")

    rule_count, approved_count = await _compute_profile_counts(profile, db)
    if approved_count < rule_count:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"{rule_count - approved_count} rule(s) are not approved. All rules must be approved before promotion.",
        )

    profile.status = "locked"
    profile.locked_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(profile)
    return _profile_response(profile, rule_count, approved_count)


@router.post("/{profile_id}/new-version", response_model=PolicyProfileResponse, status_code=status.HTTP_201_CREATED)
async def new_profile_version(
    profile_id: uuid.UUID,
    current_user: Annotated[User, Depends(require_role("admin", "security_officer"))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> PolicyProfileResponse:
    """Create a new draft version from a locked profile."""
    result = await db.execute(select(PolicyProfile).where(PolicyProfile.id == profile_id))
    profile = result.scalar_one_or_none()
    if profile is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found")
    await check_workspace_access(profile.workspace_id, current_user, db)
    if profile.status != "locked":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Only locked profiles can be versioned")

    new_profile = PolicyProfile(
        id=uuid.uuid4(),
        policy_id=profile.policy_id,
        workspace_id=profile.workspace_id,
        name=f"{profile.name} v{profile.version + 1}",
        description=profile.description,
        version=profile.version + 1,
        parent_version_id=profile.id,
        profile_type=profile.profile_type,
        included_rule_ids=profile.included_rule_ids,
        created_by=current_user.id,
    )
    db.add(new_profile)
    await db.commit()
    await db.refresh(new_profile)
    rule_count, approved_count = await _compute_profile_counts(new_profile, db)
    return _profile_response(new_profile, rule_count, approved_count)
