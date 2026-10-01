"""AURA Auth endpoints — login and token issuance."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import bcrypt
from fastapi import APIRouter, HTTPException
from jose import jwt
from pydantic import BaseModel
from sqlalchemy import select

from app.api.deps import DatabaseDep, SettingsDep
from app.database.models import User

router = APIRouter(prefix="/auth", tags=["auth"])


class LoginRequest(BaseModel):
    email: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: str
    organization_id: str
    full_name: str


@router.post("/token", response_model=TokenResponse)
async def login(body: LoginRequest, db: DatabaseDep, settings: SettingsDep):
    """Authenticate a user and return a JWT access token."""
    result = await db.execute(select(User).where(User.email == body.email, User.is_active == True))  # noqa: E712
    user = result.scalar_one_or_none()
    if not user or not user.hashed_password:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    if not bcrypt.checkpw(body.password.encode("utf-8"), user.hashed_password.encode("utf-8")):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    expire = datetime.now(UTC) + timedelta(hours=24)
    payload = {
        "sub": str(user.id),
        "org_id": str(user.organization_id),
        "exp": expire,
        "iss": settings.aura_jwt_iss,
        "aud": settings.aura_jwt_aud,
    }
    token = jwt.encode(payload, settings.aura_secret_key.get_secret_value(), algorithm=settings.aura_jwt_algorithm)
    return TokenResponse(
        access_token=token,
        user_id=str(user.id),
        organization_id=str(user.organization_id),
        full_name=user.full_name or "",
    )
