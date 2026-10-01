from collections.abc import AsyncGenerator
from typing import Any, TypeVar

import openai
from pydantic import BaseModel

from app.ai.errors.exceptions import (
    LLMAuthenticationError,
    LLMProviderError,
    LLMRateLimitError,
    LLMTimeoutError,
    LLMValidationError,
)
from app.ai.providers.base import LLMProvider
from app.ai.schemas.generation import GenerationRequest, GenerationResult
from app.ai.schemas.usage import Usage
from app.config.settings import get_settings

T = TypeVar("T", bound=BaseModel)


class OpenAIProvider(LLMProvider):
    """OpenAI implementation of the LLMProvider interface."""

    def __init__(self) -> None:
        settings = get_settings()
        api_key = settings.openai_api_key.get_secret_value() if settings.openai_api_key else None
        if not api_key:
            from fastapi import HTTPException

            raise HTTPException(
                status_code=400,
                detail="AURA AI provider is not configured. Check the LLM provider and API key.",
            )

        self.client = openai.AsyncOpenAI(
            api_key=api_key,
            timeout=settings.llm_timeout,
        )

    @property
    def name(self) -> str:
        return "openai"

    def _map_exception(self, e: Exception) -> Exception:
        """Map vendor exceptions to AURA domain exceptions."""
        if isinstance(e, openai.APITimeoutError):
            return LLMTimeoutError(f"OpenAI request timed out: {e}")
        if isinstance(e, openai.RateLimitError):
            return LLMRateLimitError(f"OpenAI rate limit exceeded: {e}")
        if isinstance(e, openai.AuthenticationError):
            return LLMAuthenticationError(f"OpenAI authentication failed: {e}")
        if isinstance(e, openai.APIError):
            return LLMProviderError(f"OpenAI API error: {e}")
        return LLMProviderError(f"Unexpected OpenAI error: {e}")

    def _prepare_messages(self, request: GenerationRequest) -> list[Any]:
        return [{"role": msg.role, "content": msg.content} for msg in request.messages]

    def _parse_usage(self, response: Any) -> Usage:
        if not hasattr(response, "usage") or not response.usage:
            return Usage()
        return Usage(
            prompt_tokens=response.usage.prompt_tokens,
            completion_tokens=response.usage.completion_tokens,
            total_tokens=response.usage.total_tokens,
        )

    async def generate(self, request: GenerationRequest) -> GenerationResult:
        messages = self._prepare_messages(request)

        try:
            response = await self.client.chat.completions.create(
                model=request.model,
                messages=messages,
                temperature=request.temperature,
                max_tokens=request.max_tokens,
            )
        except Exception as e:
            raise self._map_exception(e) from e

        choice = response.choices[0]
        return GenerationResult(
            text=choice.message.content or "",
            model=response.model,
            provider=self.name,
            usage=self._parse_usage(response),
            finish_reason=choice.finish_reason,
            raw_response=response.model_dump(),
        )

    async def generate_structured(
        self,
        request: GenerationRequest,
        schema: type[T],
    ) -> tuple[GenerationResult, T]:
        messages = self._prepare_messages(request)

        try:
            response = await self.client.beta.chat.completions.parse(
                model=request.model,
                messages=messages,
                temperature=request.temperature,
                max_tokens=request.max_tokens,
                response_format=schema,
            )
        except Exception as e:
            raise self._map_exception(e) from e

        choice = response.choices[0]

        if choice.message.parsed is None:
            raise LLMValidationError("OpenAI failed to return the requested structured format.")

        parsed_data = choice.message.parsed

        result = GenerationResult(
            text=choice.message.content or "",
            structured_data=parsed_data.model_dump(),
            model=response.model,
            provider=self.name,
            usage=self._parse_usage(response),
            finish_reason=choice.finish_reason,
            raw_response=response.model_dump(),
        )
        return result, parsed_data

    async def stream(self, request: GenerationRequest) -> AsyncGenerator[str, None]:
        messages = self._prepare_messages(request)
        try:
            stream = await self.client.chat.completions.create(
                model=request.model,
                messages=messages,
                temperature=request.temperature,
                max_tokens=request.max_tokens,
                stream=True,
            )
            async for chunk in stream:
                content = chunk.choices[0].delta.content
                if content:
                    yield content
        except Exception as e:
            raise self._map_exception(e) from e

    async def embed(self, texts: list[str], model: str) -> list[list[float]]:
        try:
            response = await self.client.embeddings.create(
                input=texts,
                model=model,
            )
            return [data.embedding for data in response.data]
        except Exception as e:
            raise self._map_exception(e) from e
