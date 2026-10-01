"""
AURA API - FastAPI Dependencies.

Provides reusable dependency injection functions for:
- Database sessions
- Settings
- Request context (request ID, current user, etc.)
- Authentication and RBAC
"""

from __future__ import annotations

import uuid
from typing import Annotated, Any

from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.settings import Settings, get_settings
from app.database.base import get_db_session
from app.database.models import User, UserRole

# =============================================================================
# Settings & Database
# =============================================================================

SettingsDep = Annotated[Settings, Depends(get_settings)]
DatabaseDep = Annotated[AsyncSession, Depends(get_db_session)]

# =============================================================================
# Request Context
# =============================================================================


def get_request_id(request: Request) -> str:
    """Extract the request ID assigned by the RequestIDMiddleware."""
    return getattr(request.state, "request_id", "unknown")


RequestIDDep = Annotated[str, Depends(get_request_id)]

# =============================================================================
# Authentication & RBAC
# =============================================================================

oauth2_scheme = HTTPBearer()


class CurrentUser(BaseModel):
    """Authenticated user context derived from a validated JWT."""

    user_id: uuid.UUID
    organization_id: uuid.UUID
    role: UserRole


def get_current_user_token(
    credentials: HTTPAuthorizationCredentials = Depends(oauth2_scheme),
    settings: Settings = Depends(get_settings),
) -> dict:
    """Validate and decode the Bearer token, returning the raw JWT payload."""
    token = credentials.credentials
    try:
        payload = jwt.decode(
            token,
            settings.aura_secret_key.get_secret_value(),
            algorithms=[settings.aura_jwt_algorithm],
            audience=settings.aura_jwt_aud,
            issuer=settings.aura_jwt_iss,
            options={"require_exp": True},
        )
        if "sub" not in payload or "org_id" not in payload:
            raise HTTPException(status_code=401, detail="Invalid token claims")
        return payload
    except JWTError as e:
        raise HTTPException(status_code=401, detail="Invalid token") from e


async def get_current_user(
    request: Request,
    token_payload: dict = Depends(get_current_user_token),
    db: AsyncSession = Depends(get_db_session),
) -> CurrentUser:
    """Resolve the JWT sub claim to a live database user and return a CurrentUser."""
    try:
        user_id = uuid.UUID(token_payload["sub"])
        result = await db.execute(select(User).where(User.id == user_id, User.is_active))
        user = result.scalars().first()
        if not user:
            raise HTTPException(status_code=401, detail="User not found or inactive")

        # Stash org_id on request state so observability middleware can access it
        request.state.organization_id = str(user.organization_id)
        return CurrentUser(
            user_id=user.id,
            organization_id=user.organization_id,
            role=user.role,
        )
    except ValueError as e:
        raise HTTPException(status_code=401, detail="Invalid UUID in token claims") from e


async def get_current_active_user(
    current_user: CurrentUser = Depends(get_current_user),
) -> CurrentUser:
    return current_user


class RequireRole:
    """Callable dependency that enforces role-based access control."""

    def __init__(self, allowed_roles: list[UserRole]) -> None:
        self.allowed_roles = allowed_roles

    def __call__(self, current_user: CurrentUser = Depends(get_current_active_user)) -> CurrentUser:
        if current_user.role not in self.allowed_roles:
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        return current_user


CurrentUserDep = Annotated[CurrentUser, Depends(get_current_active_user)]

# Legacy alias kept for backward compatibility with routes that type-annotate Any
_LegacyCurrentUserDep = Annotated[Any, Depends(get_current_active_user)]
