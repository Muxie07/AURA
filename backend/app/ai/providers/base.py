from abc import ABC, abstractmethod
from collections.abc import AsyncGenerator
from typing import TypeVar

from pydantic import BaseModel

from app.ai.schemas.generation import GenerationRequest, GenerationResult

T = TypeVar("T", bound=BaseModel)

class LLMProvider(ABC):
    """Abstract interface for all LLM providers."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Name of the provider (e.g., 'openai')."""
        pass

    @abstractmethod
    async def generate(self, request: GenerationRequest) -> GenerationResult:
        """Generate a text response."""
        pass

    @abstractmethod
    async def generate_structured(
        self,
        request: GenerationRequest,
        schema: type[T],
    ) -> tuple[GenerationResult, T]:
        """
        Generate a structured response validated against the provided Pydantic schema.
        Returns the raw result and the parsed schema instance.
        """
        pass

    @abstractmethod
    def stream(
        self, request: GenerationRequest
    ) -> AsyncGenerator[str, None]:
        """Stream a text response."""
        pass

    @abstractmethod
    async def embed(self, texts: list[str], model: str) -> list[list[float]]:
        """Generate embeddings for a list of texts."""
        pass
