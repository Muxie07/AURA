import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_cors_preflight_allowed(client: AsyncClient):
    response = await client.options(
        "/api/v1/conversations",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "authorization,content-type"
        }
    )
    assert response.status_code in (200, 204)
    assert response.headers.get("access-control-allow-origin") == "http://localhost:3000"
    assert "access-control-allow-methods" in response.headers

@pytest.mark.asyncio
async def test_cors_preflight_disallowed(client: AsyncClient):
    response = await client.options(
        "/api/v1/conversations",
        headers={
            "Origin": "http://evil.com",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "authorization,content-type"
        }
    )
    assert response.headers.get("access-control-allow-origin") is None

@pytest.mark.asyncio
async def test_cors_error_response_has_headers(client: AsyncClient):
    # This should return a 413 because it's too large, or we can just send an unauthorized request
    response = await client.get(
        "/api/v1/runs",
        headers={"Origin": "http://localhost:3000"}
    )
    assert response.status_code == 401
    assert response.headers.get("access-control-allow-origin") == "http://localhost:3000"

