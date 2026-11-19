"""
AURA API v1 - Model Providers Gateway.
Provides model routing configuration, credential management, and live health diagnostics.
"""

import time
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

import sqlalchemy as sa

from app.api.deps import CurrentUserDep, DatabaseDep

router = APIRouter(prefix="/models", tags=["Models"])

MODEL_PROVIDERS_CONFIG = [
    {
        "id": "google",
        "name": "Google Vertex AI & Gemini API",
        "status": "ACTIVE",
        "models": ["gemini-2.5-flash", "gemini-2.5-pro"],
        "latency_tier": "Ultra Low (~350ms)",
        "cost_tier": "Lowest Cost / 1M Tokens",
        "description": "Primary platform reasoning engine powering agent planning, JSON schema validation, and tool calling.",
    },
    {
        "id": "openai",
        "name": "OpenAI Enterprise Gateway",
        "status": "CONFIGURED",
        "models": ["gpt-4o", "gpt-4o-mini"],
        "latency_tier": "Low (~600ms)",
        "cost_tier": "Standard Enterprise",
        "description": "Secondary routing provider with automatic circuit breaker fallback on rate limits.",
    },
    {
        "id": "anthropic",
        "name": "Anthropic Claude Engine",
        "status": "CONFIGURED",
        "models": ["claude-3-7-sonnet", "claude-3-5-haiku"],
        "latency_tier": "Medium (~750ms)",
        "cost_tier": "High Precision Tier",
        "description": "Specialized deep document analysis and complex multi-agent contract evaluation.",
    },
    {
        "id": "heuristic",
        "name": "AURA Adaptive Heuristic & Offline Fallback",
        "status": "ACTIVE",
        "models": ["adaptive-hybrid-v1"],
        "latency_tier": "Instant (<15ms)",
        "cost_tier": "Zero Token Cost",
        "description": "Internal deterministic engine for quotations, mathematical GST computation, and catalog search.",
    },
]


class ProviderCredentialRequest(BaseModel):
    api_key: str
    custom_endpoint: str | None = None


@router.get("/providers", summary="List configured model providers")
async def list_providers(current_user: CurrentUserDep) -> dict[str, Any]:
    return {"providers": MODEL_PROVIDERS_CONFIG}


@router.post("/{provider_id}/test", summary="Test live connection to model provider")
async def test_provider_health(provider_id: str, current_user: CurrentUserDep) -> dict[str, Any]:
    """Actually calls the provider with a 1-token prompt and reports what happened.

    Previously this always called LLMService.generate() with keyword arguments
    the method doesn't accept, so the call raised on every invocation and the
    except branch unconditionally reported "HEALTHY" -- a provider that was
    unreachable, misconfigured, or didn't exist still came back healthy. It
    now builds a real GenerationRequest against the selected provider and
    reports FAILED with the real error when the call doesn't succeed.
    """
    provider = next((p for p in MODEL_PROVIDERS_CONFIG if p["id"] == provider_id), None)
    if not provider:
        raise HTTPException(status_code=404, detail=f"Model provider '{provider_id}' not found.")

    from app.ai.providers.factory import get_llm_provider
    from app.ai.schemas.generation import GenerationRequest, Message

    t0 = time.time()
    try:
        provider_impl = get_llm_provider(provider_override=provider_id)
        request = GenerationRequest(
            messages=[Message(role="user", content="ping")],
            model=provider["models"][0],
            max_tokens=10,
        )
        result = await provider_impl.generate(request)
        latency_ms = max(1, int((time.time() - t0) * 1000))
        return {
            "status": "HEALTHY",
            "provider_id": provider_id,
            "latency_ms": latency_ms,
            "message": f"Successfully verified {provider['name']} response in {latency_ms}ms.",
            "test_output": result.text[:80] if result.text else "OK",
        }
    except Exception as e:
        latency_ms = max(1, int((time.time() - t0) * 1000))
        return {
            "status": "FAILED",
            "provider_id": provider_id,
            "latency_ms": latency_ms,
            "message": f"{provider['name']} health check failed: {e}",
            "test_output": None,
        }


@router.post("/{provider_id}/credentials", summary="Save provider credentials securely")
async def update_credentials(
    provider_id: str,
    req: ProviderCredentialRequest,
    current_user: CurrentUserDep,
    db: DatabaseDep,
) -> dict[str, Any]:
    """Encrypts the API key with the tenant's derived Fernet key and persists it.

    Previously this returned a canned "saved in Vault" message without writing
    anything anywhere -- the key was discarded as soon as the request ended.
    """
    provider = next((p for p in MODEL_PROVIDERS_CONFIG if p["id"] == provider_id), None)
    if not provider:
        raise HTTPException(status_code=404, detail=f"Model provider '{provider_id}' not found.")

    from app.database.models import IntegrationCredential
    from app.security.vault import CredentialVault

    encrypted = CredentialVault.encrypt_secret(req.api_key, current_user.organization_id)

    existing = await db.scalar(
        sa.select(IntegrationCredential).where(
            IntegrationCredential.organization_id == current_user.organization_id,
            IntegrationCredential.name == provider_id,
        )
    )
    if existing:
        existing.encrypted_payload = encrypted
    else:
        db.add(
            IntegrationCredential(
                organization_id=current_user.organization_id,
                name=provider_id,
                credential_type="llm_api_key",
                encrypted_payload=encrypted,
            )
        )
    await db.commit()

    masked = req.api_key[:4] + "..." + req.api_key[-4:] if len(req.api_key) > 8 else "***"
    return {
        "status": "CONFIGURED",
        "provider_id": provider_id,
        "masked_key": masked,
        "message": f"Credentials for {provider['name']} encrypted and persisted.",
    }
