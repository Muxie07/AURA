import io
content = """\
\"\"\"
AURA API - FastAPI Dependencies.

Provides reusable dependency injection functions for:
- Database sessions
- Settings
- Request context (request ID, current user, etc.)
\"\"\"
from __future__ import annotations

import uuid
from typing import Annotated, Any

from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.settings import Settings, get_settings
from app.database.base import get_db_session
from app.database.models import User

# =============================================================================
# Settings & Database
# =============================================================================

SettingsDep = Annotated[Settings, Depends(get_settings)]
DatabaseDep = Annotated[AsyncSession, Depends(get_db_session)]

# =============================================================================
# Request Context
# =============================================================================

def get_request_id(request: Request) -> str:
    \"\"\"Extract the request ID assigned by the RequestIDMiddleware.\"\"\"
    return getattr(request.state, "request_id", "unknown")

RequestIDDep = Annotated[str, Depends(get_request_id)]

oauth2_scheme = HTTPBearer()

def get_current_user_token(
    credentials: HTTPAuthorizationCredentials = Depends(oauth2_scheme),
    settings: Settings = Depends(get_settings)
) -> dict:
    token = credentials.credentials
    try:
        payload = jwt.decode(token, settings.aura_secret_key.get_secret_value(), algorithms=["HS256"])
        if "sub" not in payload or "org_id" not in payload:
            raise HTTPException(status_code=401, detail="Invalid token claims")
        return payload
    except JWTError as e:
        raise HTTPException(status_code=401, detail="Invalid token") from e

async def get_current_user(
    token_payload: dict = Depends(get_current_user_token),
    db: AsyncSession = Depends(get_db_session)
):
    try:
        user_id = uuid.UUID(token_payload["sub"])
        result = await db.execute(select(User).where(User.id == user_id))
        user = result.scalars().first()
        if not user:
            raise HTTPException(status_code=401, detail="User not found")
        return user
    except ValueError as e:
        raise HTTPException(status_code=401, detail="Invalid UUID in token claims") from e

CurrentUserDep = Annotated[Any, Depends(get_current_user)]
"""
with io.open("backend/app/api/deps.py", "w", encoding="utf-8") as f:
    f.write(content)
