from typing import Any

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
@pytest.mark.integration
async def test_ai_generate(client: AsyncClient, monkeypatch: Any) -> None:
    monkeypatch.setenv("PRIMARY_LLM_PROVIDER", "mock")
    from app.config.settings import get_settings
    get_settings.cache_clear()

    response = await client.post(
        "/api/v1/ai/generate",
        json={"message": "Explain what AURA does."}
    )
    assert response.status_code == 200
    data = response.json()
    assert "AURA is an autonomous" in data["text"]

@pytest.mark.asyncio
@pytest.mark.integration
async def test_ai_classify(client: AsyncClient, monkeypatch: Any) -> None:
    monkeypatch.setenv("PRIMARY_LLM_PROVIDER", "mock")
    from app.config.settings import get_settings
    get_settings.cache_clear()

    response = await client.post(
        "/api/v1/ai/classify",
        json={"text": "I need a quotation"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["intent"] == "general_inquiry"
