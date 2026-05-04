"""Solution Instances router — Enforcement Stage CRUD + enforcement actions."""
from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aegis.database import get_db
from aegis.models.enforcement_job import EnforcementJob
from aegis.models.solution_instance import SolutionInstance
from aegis.models.user import User
from aegis.schemas.instance import (
    ComplianceReportResponse,
    EnforcementJobResponse,
    EnforcementRequest,
    SolutionInstanceCreate,
    SolutionInstanceResponse,
)
from aegis.services.rbac import check_workspace_access, get_current_user, require_role

router = APIRouter(prefix="/instances", tags=["instances"])


@router.post("", response_model=SolutionInstanceResponse, status_code=status.HTTP_201_CREATED)
async def create_instance(
    body: SolutionInstanceCreate,
    current_user: Annotated[User, Depends(require_role("admin", "security_officer"))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> SolutionInstanceResponse:
    await check_workspace_access(body.workspace_id, current_user, db)
    inst = SolutionInstance(
        id=uuid.uuid4(),
        workspace_id=body.workspace_id,
        name=body.name,
        solution_type_id=body.solution_type_id,
        profile_id=body.profile_id,
        owner_id=current_user.id,
    )
    db.add(inst)
    await db.commit()
    await db.refresh(inst)
    return SolutionInstanceResponse.model_validate(inst)


@router.get("", response_model=list[SolutionInstanceResponse])
async def list_instances(
    workspace_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[SolutionInstanceResponse]:
    await check_workspace_access(workspace_id, current_user, db)
    result = await db.execute(
        select(SolutionInstance)
        .where(SolutionInstance.workspace_id == workspace_id)
        .order_by(SolutionInstance.name)
    )
    return [SolutionInstanceResponse.model_validate(i) for i in result.scalars().all()]


@router.get("/{instance_id}", response_model=SolutionInstanceResponse)
async def get_instance(
    instance_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> SolutionInstanceResponse:
    result = await db.execute(select(SolutionInstance).where(SolutionInstance.id == instance_id))
    inst = result.scalar_one_or_none()
    if inst is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Instance not found")
    await check_workspace_access(inst.workspace_id, current_user, db)
    return SolutionInstanceResponse.model_validate(inst)


def _create_enforcement_job(instance_id: uuid.UUID, job_type: str, user_id: uuid.UUID) -> EnforcementJob:
    return EnforcementJob(
        id=uuid.uuid4(),
        instance_id=instance_id,
        job_type=job_type,
        status="pending",
        created_by=user_id,
    )


@router.post("/{instance_id}/evaluate", response_model=EnforcementJobResponse, status_code=status.HTTP_202_ACCEPTED)
async def evaluate(
    instance_id: uuid.UUID,
    current_user: Annotated[User, Depends(require_role("admin", "security_officer", "auditor"))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> EnforcementJobResponse:
    from aegis.tasks.enforcement_tasks import evaluate_instance
    result = await db.execute(select(SolutionInstance).where(SolutionInstance.id == instance_id))
    if result.scalar_one_or_none() is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Instance not found")
    job = _create_enforcement_job(instance_id, "evaluate", current_user.id)
    db.add(job)
    await db.commit()
    task = evaluate_instance.delay(str(job.id), str(instance_id))
    job.celery_task_id = task.id
    await db.commit()
    await db.refresh(job)
    return EnforcementJobResponse.model_validate(job)


@router.post("/{instance_id}/remediate", response_model=EnforcementJobResponse, status_code=status.HTTP_202_ACCEPTED)
async def remediate(
    instance_id: uuid.UUID,
    body: EnforcementRequest,
    current_user: Annotated[User, Depends(require_role("admin", "security_officer"))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> EnforcementJobResponse:
    from aegis.tasks.enforcement_tasks import remediate_instance
    result = await db.execute(select(SolutionInstance).where(SolutionInstance.id == instance_id))
    if result.scalar_one_or_none() is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Instance not found")
    job = _create_enforcement_job(instance_id, "remediate", current_user.id)
    db.add(job)
    await db.commit()
    rule_ids = [str(r) for r in body.rule_ids] if body.rule_ids else None
    task = remediate_instance.delay(str(job.id), str(instance_id), rule_ids)
    job.celery_task_id = task.id
    await db.commit()
    await db.refresh(job)
    return EnforcementJobResponse.model_validate(job)


@router.post("/{instance_id}/rollback", response_model=EnforcementJobResponse, status_code=status.HTTP_202_ACCEPTED)
async def rollback(
    instance_id: uuid.UUID,
    body: EnforcementRequest,
    current_user: Annotated[User, Depends(require_role("admin", "security_officer"))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> EnforcementJobResponse:
    from aegis.tasks.enforcement_tasks import rollback_instance
    result = await db.execute(select(SolutionInstance).where(SolutionInstance.id == instance_id))
    if result.scalar_one_or_none() is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Instance not found")
    job = _create_enforcement_job(instance_id, "rollback", current_user.id)
    db.add(job)
    await db.commit()
    rule_ids = [str(r) for r in body.rule_ids] if body.rule_ids else None
    task = rollback_instance.delay(str(job.id), str(instance_id), rule_ids)
    job.celery_task_id = task.id
    await db.commit()
    await db.refresh(job)
    return EnforcementJobResponse.model_validate(job)


@router.post("/{instance_id}/dry-run", response_model=EnforcementJobResponse, status_code=status.HTTP_202_ACCEPTED)
async def dry_run(
    instance_id: uuid.UUID,
    current_user: Annotated[User, Depends(require_role("admin", "security_officer", "auditor"))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> EnforcementJobResponse:
    from aegis.tasks.enforcement_tasks import dry_run_instance
    result = await db.execute(select(SolutionInstance).where(SolutionInstance.id == instance_id))
    if result.scalar_one_or_none() is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Instance not found")
    job = _create_enforcement_job(instance_id, "dry_run", current_user.id)
    db.add(job)
    await db.commit()
    task = dry_run_instance.delay(str(job.id), str(instance_id))
    job.celery_task_id = task.id
    await db.commit()
    await db.refresh(job)
    return EnforcementJobResponse.model_validate(job)


@router.get("/{instance_id}/jobs", response_model=list[EnforcementJobResponse])
async def list_jobs(
    instance_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[EnforcementJobResponse]:
    result = await db.execute(
        select(EnforcementJob)
        .where(EnforcementJob.instance_id == instance_id)
        .order_by(EnforcementJob.created_at.desc())
    )
    return [EnforcementJobResponse.model_validate(j) for j in result.scalars().all()]


@router.delete("/{instance_id}", status_code=status.HTTP_204_NO_CONTENT, response_model=None)
async def delete_instance(
    instance_id: uuid.UUID,
    current_user: Annotated[User, Depends(require_role("admin", "security_officer"))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> None:
    result = await db.execute(select(SolutionInstance).where(SolutionInstance.id == instance_id))
    inst = result.scalar_one_or_none()
    if inst is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Instance not found")
    await check_workspace_access(inst.workspace_id, current_user, db)
    await db.delete(inst)
    await db.commit()
