import uuid
from typing import Any, Literal

from pydantic import BaseModel, Field

from app.ai.schemas.usage import Usage

Role = Literal["system", "user", "assistant", "tool"]

class Message(BaseModel):
    """A single message in a conversation."""
    role: Role
    content: str
    name: str | None = None
    tool_calls: list[dict[str, Any]] | None = None

class GenerationRequest(BaseModel):
    """Normalized request sent to an LLM provider."""
    messages: list[Message] = Field(description="Conversation history.")
    model: str = Field(description="Model identifier (e.g., 'gpt-4o').")
    temperature: float = Field(default=0.1, description="Sampling temperature.")
    max_tokens: int | None = Field(default=None, description="Maximum tokens to generate.")
    response_format: dict[str, Any] | None = Field(default=None, description="Structured output schema if requested.")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Additional provider-specific parameters.")
    organization_id: uuid.UUID | None = None

class GenerationResult(BaseModel):
    """Normalized response from an LLM provider."""
    text: str = Field(default="", description="Generated text.")
    structured_data: dict[str, Any] | None = Field(default=None, description="Parsed structured data if requested.")
    model: str = Field(description="Model used for generation.")
    provider: str = Field(description="Provider used for generation.")
    usage: Usage = Field(default_factory=Usage, description="Token usage.")
    finish_reason: str | None = Field(default=None, description="Reason generation stopped.")
    raw_response: dict[str, Any] = Field(default_factory=dict, description="Raw provider response for debugging.")
