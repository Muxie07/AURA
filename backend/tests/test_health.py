"""
AURA Tests — Health Endpoints.

Tests the /health and /ping endpoints for correct responses,
database connectivity checks, and proper status code behavior.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from httpx import AsyncClient


@pytest.mark.asyncio
async def test_root_health_returns_ok(client: AsyncClient) -> None:
    """Root /health liveness probe should return 200 with status ok."""
    response = await client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "version" in data


@pytest.mark.asyncio
async def test_api_v1_health_returns_healthy(client: AsyncClient) -> None:
    """
    GET /api/v1/health should return 200 when database is reachable.

    In the test environment, the database session is the SQLite in-memory
    fixture which is always available.
    """
    response = await client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "timestamp" in data
    assert "version" in data
    assert "environment" in data
    assert "components" in data
    assert "database" in data["components"]
    assert data["components"]["database"]["status"] == "healthy"
    assert data["components"]["database"]["latency_ms"] is not None


@pytest.mark.asyncio
async def test_ping_returns_ok(client: AsyncClient) -> None:
    """GET /api/v1/ping should return 200."""
    response = await client.get("/api/v1/ping")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


@pytest.mark.asyncio
async def test_health_includes_request_id(client: AsyncClient) -> None:
    """Every response should include X-Request-ID header."""
    response = await client.get("/health")
    assert "x-request-id" in response.headers


@pytest.mark.asyncio
async def test_health_propagates_request_id(client: AsyncClient) -> None:
    """If the client sends X-Request-ID, it should be echoed back."""
    custom_id = "my-custom-request-id-12345"
    response = await client.get("/health", headers={"X-Request-ID": custom_id})
    assert response.headers.get("x-request-id") == custom_id


@pytest.mark.asyncio
async def test_invalid_request_id_gets_replaced(client: AsyncClient) -> None:
    """Suspicious X-Request-ID values should be rejected and replaced."""
    malicious_id = "<script>alert(1)</script>"
    response = await client.get("/health", headers={"X-Request-ID": malicious_id})
    # The response header should NOT contain the malicious value
    assert response.headers.get("x-request-id") != malicious_id
    # A new UUID should have been assigned
    assert len(response.headers.get("x-request-id", "")) > 0
