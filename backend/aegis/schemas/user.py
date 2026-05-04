"""User schemas."""
from __future__ import annotations
import uuid
from datetime import datetime
from pydantic import BaseModel, ConfigDict, EmailStr


class UserCreate(BaseModel):
    email: EmailStr
    username: str
    password: str
    role: str = "user"


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: str
    username: str
    role: str
    is_active: bool
    created_at: datetime


class UserRoleUpdate(BaseModel):
    role: str
