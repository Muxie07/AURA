from typing import Any, ClassVar

from app.ai.errors.exceptions import PromptNotFoundError


class PromptRegistry:
    """
    Central registry for system prompts.
    Decouples prompt text from business logic.
    """

    _prompts: ClassVar[dict[str, dict[str, Any]]] = {
        "intent_classification:v1": {
            "system_prompt": "You are an expert intent classifier. Determine the intent of the user message.",
            "version": "1.0",
            "metadata": {"task": "classification"},
        },
        "default:v1": {
            "system_prompt": "You are AURA, an autonomous AI business operations engineer.",
            "version": "1.0",
            "metadata": {"task": "general"},
        },
    }

    @classmethod
    def get(cls, name: str) -> str:
        """
        Get a system prompt by name (e.g., 'intent_classification:v1').
        """
        prompt_data = cls._prompts.get(name)
        if not prompt_data:
            raise PromptNotFoundError(f"Prompt '{name}' not found in registry.")
        return str(prompt_data["system_prompt"])
