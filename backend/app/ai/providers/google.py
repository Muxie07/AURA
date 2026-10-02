from collections.abc import AsyncGenerator
from typing import Any, TypeVar

from pydantic import BaseModel

try:
    from google import genai
    from google.genai import types
except ImportError:
    genai = None  # type: ignore

from app.ai.errors.exceptions import (
    LLMAuthenticationError,
    LLMProviderError,
    LLMQuotaExceededError,
    LLMRateLimitError,
    LLMTimeoutError,
    LLMValidationError,
    LLMContentBlockedError,
)
from app.ai.providers.base import LLMProvider
from app.ai.schemas.generation import GenerationRequest, GenerationResult
from app.ai.schemas.usage import Usage
from app.config.settings import get_settings

T = TypeVar("T", bound=BaseModel)


class GeminiProvider(LLMProvider):
    """Google Gemini implementation of the LLMProvider interface."""

    def __init__(self) -> None:
        if genai is None:
            raise LLMProviderError("google-genai package is not installed.")

        settings = get_settings()
        api_key = (
            settings.google_ai_api_key.get_secret_value() if settings.google_ai_api_key else None
        )

        if not api_key:
            import os

            api_key = os.getenv("GEMINI_API_KEY")

        if not api_key:
            from fastapi import HTTPException

            raise HTTPException(
                status_code=400,
                detail="AURA AI provider is not configured. Check the LLM provider and API key.",
            )

        self.client = genai.Client(api_key=api_key)

    @property
    def name(self) -> str:
        return "google"

    def _map_exception(self, e: Exception) -> Exception:
        """Map vendor exceptions to AURA domain exceptions."""
        try:
            from google.genai.errors import APIError

            if isinstance(e, APIError):
                if e.code == 401 or e.code == 403:
                    return LLMAuthenticationError(f"Gemini authentication failed: {e}")
                if e.code == 429:
                    # Check if it's a hard quota limit vs a temporary burst limit
                    if "GenerateRequestsPerDay" in str(e) or "quota" in str(e).lower():
                        return LLMQuotaExceededError(
                            f"Gemini quota exhausted (429): {e}", provider="gemini", status=429
                        )
                    return LLMRateLimitError(f"Gemini temporary rate limit (429): {e}")
                if e.code == 500 or e.code == 503:
                    return LLMRateLimitError(f"Gemini temporary availability issue: {e}")
                if e.code == 504:
                    return LLMTimeoutError(f"Gemini request timed out: {e}")
                return LLMProviderError(f"Gemini API error: {e}")

        except ImportError:
            pass
        return LLMProviderError(f"Unexpected Gemini error: {e}")

    def _prepare_messages(self, request: GenerationRequest) -> list[Any]:
        contents = []
        for msg in request.messages:
            gemini_role: str = msg.role
            if gemini_role == "assistant":
                gemini_role = "model"
            elif gemini_role == "system":
                gemini_role = "user"

            contents.append(
                types.Content(role=gemini_role, parts=[types.Part.from_text(text=msg.content)])
            )
        return contents

    def _parse_usage(self, response: Any) -> Usage:
        if not hasattr(response, "usage_metadata") or not response.usage_metadata:
            return Usage(prompt_tokens=0, completion_tokens=0, total_tokens=0)
        return Usage(
            prompt_tokens=response.usage_metadata.prompt_token_count or 0,
            completion_tokens=response.usage_metadata.candidates_token_count or 0,
            total_tokens=response.usage_metadata.total_token_count or 0,
        )

    async def generate(self, request: GenerationRequest) -> GenerationResult:
        contents = self._prepare_messages(request)
        config = types.GenerateContentConfig(
            temperature=request.temperature,
            max_output_tokens=request.max_tokens,
        )

        import asyncio

        settings = get_settings()
        timeout = settings.llm_timeout

        try:
            response = await asyncio.wait_for(
                self.client.aio.models.generate_content(
                    model=request.model,
                    contents=contents,
                    config=config,
                ),
                timeout=timeout,
            )
        except TimeoutError as e:
            raise LLMTimeoutError(f"Gemini request timed out after {timeout} seconds") from e
        except Exception as e:
            raise self._map_exception(e) from e

        if not response.candidates:
            raise LLMProviderError("No response candidates returned by Gemini.")
            
        finish_reason = response.candidates[0].finish_reason
        if finish_reason and str(finish_reason).upper() == "SAFETY":
            raise LLMContentBlockedError("Gemini blocked response due to safety filters.")


        candidate = response.candidates[0]
        text = response.text or ""

        return GenerationResult(
            text=text,
            model=request.model,
            provider=self.name,
            usage=self._parse_usage(response),
            finish_reason=str(candidate.finish_reason),
            raw_response={"text": text},
        )

    async def generate_structured(
        self,
        request: GenerationRequest,
        schema: type[T],
    ) -> tuple[GenerationResult, T]:
        schema_dict = schema.model_json_schema()

        def remove_additional_properties(d):
            if isinstance(d, dict):
                d.pop("additionalProperties", None)
                for v in d.values():
                    remove_additional_properties(v)
            elif isinstance(d, list):
                for item in d:
                    remove_additional_properties(item)

        remove_additional_properties(schema_dict)

        contents = self._prepare_messages(request)
        config = types.GenerateContentConfig(
            temperature=request.temperature,
            max_output_tokens=request.max_tokens,
            response_mime_type="application/json",
            response_schema=schema_dict,
        )

        import asyncio

        settings = get_settings()
        timeout = settings.llm_timeout

        try:
            response = await asyncio.wait_for(
                self.client.aio.models.generate_content(
                    model=request.model,
                    contents=contents,
                    config=config,
                ),
                timeout=timeout,
            )
        except TimeoutError as e:
            raise LLMTimeoutError(f"Gemini request timed out after {timeout} seconds") from e
        except Exception as e:
            raise self._map_exception(e) from e

        if not response.candidates:
            raise LLMProviderError("No response candidates returned by Gemini.")
            
        finish_reason = response.candidates[0].finish_reason
        if finish_reason and str(finish_reason).upper() == "SAFETY":
            raise LLMContentBlockedError("Gemini blocked response due to safety filters.")


        candidate = response.candidates[0]
        text = response.text or ""

        try:
            parsed_data = schema.model_validate_json(text)
        except Exception as e:
            raise LLMValidationError(f"Failed to parse structured data from Gemini: {e}") from e

        result = GenerationResult(
            text=text,
            structured_data=parsed_data.model_dump(),
            model=request.model,
            provider=self.name,
            usage=self._parse_usage(response),
            finish_reason=str(candidate.finish_reason),
            raw_response={"text": text},
        )
        return result, parsed_data

    async def stream(self, request: GenerationRequest) -> AsyncGenerator[str, None]:
        contents = self._prepare_messages(request)
        config = types.GenerateContentConfig(
            temperature=request.temperature,
            max_output_tokens=request.max_tokens,
        )

        try:
            stream = await self.client.aio.models.generate_content_stream(
                model=request.model,
                contents=contents,
                config=config,
            )
            async for chunk in stream:
                if chunk.text:
                    yield chunk.text
        except Exception as e:
            raise self._map_exception(e) from e

    async def embed(self, texts: list[str], model: str) -> list[list[float]]:
        if "text-embedding" in model or model == "text-embedding-3-small":
            model = "gemini-embedding-2"
        try:
            response = await self.client.aio.models.embed_content(
                model=model,
                contents=texts,  # type: ignore
            )
            # Pad to 1536 dimensions for AURA DB compatibility
            result = []
            if not response.embeddings:
                return []
            for emb in response.embeddings:
                vec: list[float] = emb.values or []
                if len(vec) < 1536:
                    vec.extend([0.0] * (1536 - len(vec)))
                elif len(vec) > 1536:
                    vec = vec[:1536]
                result.append(vec)
            return result
        except Exception as e:
            raise self._map_exception(e) from e
