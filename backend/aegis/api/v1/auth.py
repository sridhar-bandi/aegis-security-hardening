"""Auth router — login and register."""
from __future__ import annotations

from typing import Annotated
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from aegis.database import get_db
from aegis.models.user import User
from aegis.schemas.auth import LoginRequest, TokenResponse
from aegis.schemas.user import UserCreate, UserResponse
from aegis.services.rbac import create_access_token, hash_password, verify_password

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest, db: Annotated[AsyncSession, Depends(get_db)]) -> TokenResponse:
    result = await db.execute(
        select(User).where(or_(User.email == body.identifier, User.username == body.identifier))
    )
    user = result.scalar_one_or_none()
    if user is None or not verify_password(body.password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account inactive")
    token = create_access_token(str(user.id), user.role)
    return TokenResponse(access_token=token)


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(body: UserCreate, db: Annotated[AsyncSession, Depends(get_db)]) -> UserResponse:
    # Check unique email
    result = await db.execute(select(User).where(User.email == body.email))
    if result.scalar_one_or_none() is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered")
    user = User(
        id=uuid.uuid4(),
        email=body.email,
        username=body.username,
        hashed_password=hash_password(body.password),
        role="user",  # registration always creates regular users
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return UserResponse.model_validate(user)
