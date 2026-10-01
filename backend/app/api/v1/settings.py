from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from sqlalchemy import select

from app.api.deps import CurrentUserDep, DatabaseDep, SettingsDep
from app.database.models import Organization

router = APIRouter(prefix="/settings", tags=["settings"])


class SettingsUpdate(BaseModel):
    settings: dict[str, Any]


@router.get("")
async def get_settings(
    current_user: CurrentUserDep, db: DatabaseDep, app_settings: SettingsDep
) -> dict[str, Any]:
    # Merge Environment settings with Organization Database settings
    result = await db.execute(
        select(Organization).where(Organization.id == current_user.organization_id)
    )
    org = result.scalar_one_or_none()
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")

    env_settings = {
        "aura_env": app_settings.aura_env,
        "llm_provider": app_settings.primary_llm_provider,
        "llm_model": app_settings.primary_llm_model,
        "llm_fallback_model": app_settings.fallback_llm_model,
        "llm_embedding_model": app_settings.embedding_model,
        "llm_temperature": app_settings.model_temperature,
        "db_url_configured": bool(app_settings.database_url),
        "redis_url_configured": bool(app_settings.redis_url),
    }

    return {
        "organization": {
            "id": str(org.id),
            "name": org.name,
            "slug": org.slug,
        },
        "environment": env_settings,
        "user_settings": org.settings or {},
    }


@router.patch("")
async def update_settings(
    req: SettingsUpdate, current_user: CurrentUserDep, db: DatabaseDep
) -> dict[str, Any]:
    result = await db.execute(
        select(Organization).where(Organization.id == current_user.organization_id)
    )
    org = result.scalar_one_or_none()
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")

    # Update json
    current_settings = dict(org.settings or {})
    current_settings.update(req.settings)
    org.settings = current_settings
    await db.commit()

    return {"status": "success", "settings": org.settings}
