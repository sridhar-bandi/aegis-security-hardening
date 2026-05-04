"""Auth schemas."""
from __future__ import annotations
from pydantic import BaseModel


class LoginRequest(BaseModel):
    identifier: str  # email address or username
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class TokenPayload(BaseModel):
    sub: str  # user_id
    role: str
    exp: int
