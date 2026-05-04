"""Solution Types router — Development Stage component tree."""
from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aegis.database import get_db
from aegis.models.solution_type import SolutionType
from aegis.models.user import User
from aegis.schemas.solution_type import (
    ComponentSelectionUpdate,
    SolutionTypeCreate,
    SolutionTypeResponse,
)
from aegis.services.rbac import check_workspace_access, get_current_user, require_role

router = APIRouter(prefix="/solution-types", tags=["solution-types"])


@router.post("", response_model=SolutionTypeResponse, status_code=status.HTTP_201_CREATED)
async def create_solution_type(
    body: SolutionTypeCreate,
    current_user: Annotated[User, Depends(require_role("admin", "security_officer"))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> SolutionTypeResponse:
    await check_workspace_access(body.workspace_id, current_user, db)
    st = SolutionType(
        id=uuid.uuid4(),
        workspace_id=body.workspace_id,
        name=body.name,
        description=body.description,
        created_by=current_user.id,
    )
    db.add(st)
    await db.commit()
    await db.refresh(st)
    return SolutionTypeResponse.model_validate(st)


@router.get("", response_model=list[SolutionTypeResponse])
async def list_solution_types(
    workspace_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[SolutionTypeResponse]:
    await check_workspace_access(workspace_id, current_user, db)
    result = await db.execute(
        select(SolutionType).where(SolutionType.workspace_id == workspace_id).order_by(SolutionType.name)
    )
    return [SolutionTypeResponse.model_validate(s) for s in result.scalars().all()]


@router.get("/{st_id}", response_model=SolutionTypeResponse)
async def get_solution_type(
    st_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> SolutionTypeResponse:
    result = await db.execute(select(SolutionType).where(SolutionType.id == st_id))
    st = result.scalar_one_or_none()
    if st is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="SolutionType not found")
    await check_workspace_access(st.workspace_id, current_user, db)
    return SolutionTypeResponse.model_validate(st)


@router.patch("/{st_id}/components", response_model=SolutionTypeResponse)
async def update_component_selection(
    st_id: uuid.UUID,
    body: ComponentSelectionUpdate,
    current_user: Annotated[User, Depends(require_role("admin", "security_officer"))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> SolutionTypeResponse:
    result = await db.execute(select(SolutionType).where(SolutionType.id == st_id))
    st = result.scalar_one_or_none()
    if st is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="SolutionType not found")
    await check_workspace_access(st.workspace_id, current_user, db)
    st.component_selection = body.selected_component_ids
    await db.commit()
    await db.refresh(st)
    return SolutionTypeResponse.model_validate(st)


@router.delete("/{st_id}", status_code=status.HTTP_204_NO_CONTENT, response_model=None)
async def delete_solution_type(
    st_id: uuid.UUID,
    current_user: Annotated[User, Depends(require_role("admin", "security_officer"))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> None:
    result = await db.execute(select(SolutionType).where(SolutionType.id == st_id))
    st = result.scalar_one_or_none()
    if st is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="SolutionType not found")
    await check_workspace_access(st.workspace_id, current_user, db)
    await db.delete(st)
    await db.commit()
