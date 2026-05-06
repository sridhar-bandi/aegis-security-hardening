"""Solution Instances router — Enforcement Stage CRUD + enforcement actions."""
from __future__ import annotations

import json
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
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
        blueprint_id=body.blueprint_id,
        scid_json=body.scid_json,
        scid_filename=body.scid_filename,
        owner_id=current_user.id,
    )
    db.add(inst)
    await db.commit()
    await db.refresh(inst)
    return SolutionInstanceResponse.model_validate(inst)


@router.post("/upload", response_model=SolutionInstanceResponse, status_code=status.HTTP_201_CREATED)
async def create_instance_with_scid_upload(
    workspace_id: Annotated[str, Form()],
    name: Annotated[str, Form()],
    current_user: Annotated[User, Depends(require_role("admin", "security_officer"))],
    db: Annotated[AsyncSession, Depends(get_db)],
    solution_type_id: Annotated[str | None, Form()] = None,
    blueprint_id: Annotated[str | None, Form()] = None,
    scid_file: UploadFile | None = File(None),
) -> SolutionInstanceResponse:
    """Create an instance with an optional SCID JSON file upload containing infrastructure credentials."""
    ws_id = uuid.UUID(workspace_id)
    await check_workspace_access(ws_id, current_user, db)

    scid_data = None
    scid_filename = None
    if scid_file and scid_file.filename:
        if not scid_file.content_type or "json" not in scid_file.content_type:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="SCID file must be a JSON file",
            )
        raw = await scid_file.read()
        if len(raw) > 10 * 1024 * 1024:  # 10 MB limit
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail="SCID file exceeds 10 MB limit",
            )
        try:
            scid_data = json.loads(raw)
        except (json.JSONDecodeError, UnicodeDecodeError):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="SCID file is not valid JSON",
            )
        scid_filename = scid_file.filename

    inst = SolutionInstance(
        id=uuid.uuid4(),
        workspace_id=ws_id,
        name=name,
        solution_type_id=uuid.UUID(solution_type_id) if solution_type_id else None,
        blueprint_id=uuid.UUID(blueprint_id) if blueprint_id else None,
        scid_json=scid_data,
        scid_filename=scid_filename,
        owner_id=current_user.id,
    )
    db.add(inst)
    await db.commit()
    await db.refresh(inst)
    return SolutionInstanceResponse.model_validate(inst)


@router.put("/{instance_id}/scid", response_model=SolutionInstanceResponse)
async def upload_scid(
    instance_id: uuid.UUID,
    current_user: Annotated[User, Depends(require_role("admin", "security_officer"))],
    db: Annotated[AsyncSession, Depends(get_db)],
    scid_file: UploadFile = File(...),
) -> SolutionInstanceResponse:
    """Upload or replace the SCID JSON for an existing instance."""
    result = await db.execute(select(SolutionInstance).where(SolutionInstance.id == instance_id))
    inst = result.scalar_one_or_none()
    if inst is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Instance not found")
    await check_workspace_access(inst.workspace_id, current_user, db)

    if not scid_file.content_type or "json" not in scid_file.content_type:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="SCID file must be a JSON file",
        )
    raw = await scid_file.read()
    if len(raw) > 10 * 1024 * 1024:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="SCID file exceeds 10 MB limit",
        )
    try:
        scid_data = json.loads(raw)
    except (json.JSONDecodeError, UnicodeDecodeError):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="SCID file is not valid JSON",
        )

    inst.scid_json = scid_data
    inst.scid_filename = scid_file.filename
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
