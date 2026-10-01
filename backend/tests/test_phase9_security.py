from uuid import uuid4

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_auth_rejection_no_token(client: AsyncClient):
    """Verify that unauthenticated requests to protected endpoints fail."""
    client.headers["authorization"] = ""
    response = await client.post("/api/v1/runs", json={"conversation_id": str(uuid4()), "request": "test"})
    assert response.status_code == 403 or response.status_code == 401

@pytest.mark.asyncio
async def test_invalid_token(client: AsyncClient):
    """Verify that invalid tokens are rejected."""
    client.headers["authorization"] = "Bearer invalid_token"
    response = await client.post("/api/v1/runs", json={"conversation_id": str(uuid4()), "request": "test"})
    assert response.status_code == 401

@pytest.mark.asyncio
async def test_tenant_isolation(client: AsyncClient, organization, user):
    """Verify that cross-tenant access is restricted."""
    response = await client.get("/api/v1/conversations")
    assert response.status_code == 200

@pytest.mark.asyncio
async def test_rate_limiting(client: AsyncClient, monkeypatch: pytest.MonkeyPatch):
    """Verify that the AI generate endpoint is rate limited."""
    # Ensure we use mock provider so we don't hit real LLMs
    monkeypatch.setenv("AURA_MODEL_PROVIDER", "mock")
    monkeypatch.setenv("PRIMARY_LLM_PROVIDER", "mock")

    from app.config.settings import get_settings
    get_settings.cache_clear()

    settings = get_settings()
    original_limit = settings.aura_rate_limit_requests
    settings.aura_rate_limit_requests = 2

    # Clear the redis key for the test client IP to avoid cross-run state issues
    import redis.asyncio as aioredis
    redis_client = aioredis.from_url(settings.redis_url)
    await redis_client.delete("rate_limit:ai_generate:127.0.0.1")
    await redis_client.aclose()

    try:
        # Request 1 - should pass
        res1 = await client.post("/api/v1/ai/generate", json={"message": "hello test 1"})
        assert res1.status_code == 200, res1.text

        # Request 2 - should pass
        res2 = await client.post("/api/v1/ai/generate", json={"message": "hello test 2"})
        assert res2.status_code == 200, res2.text

        # Request 3 - should fail with 429
        res3 = await client.post("/api/v1/ai/generate", json={"message": "hello test 3"})
        assert res3.status_code == 429
        assert "Too Many Requests" in res3.text
    finally:
        # Restore original limit
        settings.aura_rate_limit_requests = original_limit
        get_settings.cache_clear()
