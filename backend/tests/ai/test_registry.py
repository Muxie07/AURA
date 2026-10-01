import pytest

from app.ai.errors.exceptions import PromptNotFoundError
from app.ai.prompts.registry import PromptRegistry


def test_registry_get_valid() -> None:
    prompt = PromptRegistry.get("default:v1")
    assert "AURA" in prompt


def test_registry_get_invalid() -> None:
    with pytest.raises(PromptNotFoundError):
        PromptRegistry.get("invalid_does_not_exist:v1")
