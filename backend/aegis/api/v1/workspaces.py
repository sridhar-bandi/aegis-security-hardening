"""Workspaces router."""
from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aegis.database import get_db
from aegis.models.user import User
from aegis.models.workspace import Workspace, WorkspaceMember
from aegis.schemas.workspace import WorkspaceCreate, WorkspaceMemberAdd, WorkspaceResponse
from aegis.services.rbac import check_workspace_access, get_current_user, require_role

router = APIRouter(prefix="/workspaces", tags=["workspaces"])


@router.post("", response_model=WorkspaceResponse, status_code=status.HTTP_201_CREATED)
async def create_workspace(
    body: WorkspaceCreate,
    current_user: Annotated[User, Depends(require_role("admin", "security_officer"))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> WorkspaceResponse:
    ws = Workspace(id=uuid.uuid4(), name=body.name, description=body.description, owner_id=current_user.id)
    db.add(ws)
    await db.commit()
    await db.refresh(ws)
    return WorkspaceResponse.model_validate(ws)


@router.get("", response_model=list[WorkspaceResponse])
async def list_workspaces(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[WorkspaceResponse]:
    if current_user.role == "admin":
        result = await db.execute(select(Workspace).order_by(Workspace.name))
        workspaces = result.scalars().all()
    else:
        result = await db.execute(
            select(Workspace)
            .join(WorkspaceMember, WorkspaceMember.workspace_id == Workspace.id)
            .where(WorkspaceMember.user_id == current_user.id)
        )
        workspaces = result.scalars().all()
    return [WorkspaceResponse.model_validate(w) for w in workspaces]


@router.get("/{workspace_id}", response_model=WorkspaceResponse)
async def get_workspace(
    workspace_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> WorkspaceResponse:
    result = await db.execute(select(Workspace).where(Workspace.id == workspace_id))
    ws = result.scalar_one_or_none()
    if ws is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workspace not found")
    await check_workspace_access(workspace_id, current_user, db)
    return WorkspaceResponse.model_validate(ws)


@router.delete("/{workspace_id}", status_code=status.HTTP_204_NO_CONTENT, response_model=None)
async def delete_workspace(
    workspace_id: uuid.UUID,
    current_user: Annotated[User, Depends(require_role("admin", "security_officer"))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> None:
    result = await db.execute(select(Workspace).where(Workspace.id == workspace_id))
    ws = result.scalar_one_or_none()
    if ws is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workspace not found")
    if current_user.role != "admin" and ws.owner_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only workspace owner or admin can delete")
    await db.delete(ws)
    await db.commit()


@router.post("/{workspace_id}/members", status_code=status.HTTP_201_CREATED)
async def add_member(
    workspace_id: uuid.UUID,
    body: WorkspaceMemberAdd,
    current_user: Annotated[User, Depends(require_role("admin", "security_officer"))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    result = await db.execute(select(Workspace).where(Workspace.id == workspace_id))
    if result.scalar_one_or_none() is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workspace not found")
    member = WorkspaceMember(
        id=uuid.uuid4(), workspace_id=workspace_id, user_id=body.user_id, role=body.role
    )
    db.add(member)
    await db.commit()
    return {"status": "added", "user_id": str(body.user_id)}
