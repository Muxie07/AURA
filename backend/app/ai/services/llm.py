import time
from collections.abc import AsyncGenerator
from typing import Any, TypeVar

import structlog
from pydantic import BaseModel
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from app.ai.errors.exceptions import LLMRateLimitError, LLMTimeoutError
from app.ai.providers.factory import get_llm_provider
from app.ai.routing.router import ModelRouter
from app.ai.schemas.generation import GenerationRequest, GenerationResult, Message
from app.config.settings import get_settings

logger = structlog.get_logger(__name__)

T = TypeVar("T", bound=BaseModel)

class LLMService:
    """
    Application-facing service for all AI generation operations.
    Handles routing, provider execution, retries, fallbacks, and observability.
    """
    def __init__(self) -> None:
        self.settings = get_settings()
        from app.ai.providers.factory import get_llm_provider
        self.provider = get_llm_provider()
        
        self.fallback_provider = None
        if self.settings.fallback_llm_provider:
            try:
                self.fallback_provider = get_llm_provider(self.settings.fallback_llm_provider)
            except Exception as e:
                import structlog
                structlog.get_logger(__name__).warning("fallback_provider_init_failed", error=str(e))

    def _get_retry_decorator(self) -> Any:
        return retry(
            retry=retry_if_exception_type((LLMTimeoutError, LLMRateLimitError)),
            stop=stop_after_attempt(self.settings.llm_retry_max),
            wait=wait_exponential(multiplier=self.settings.llm_retry_delay),
            reraise=True,
        )

    def _check_budget_before_run(self, request: GenerationRequest, model: str) -> None:
        if not request.organization_id:
            return

        from app.evaluation.cost import CostManager
        from app.evaluation.schemas import BudgetStatus

        prompt_chars = sum(len(m.content) for m in request.messages if m.content)
        est_tokens = int(prompt_chars / 3.0)

        # Estimate with a reasonable output length
        est_cost = CostManager.estimate_cost(model, self.provider.name, est_tokens, 500)
        check = CostManager.check_budget(
            organization_id=request.organization_id,
            estimated_cost_usd=est_cost.estimated_cost_usd
        )

        if check.status == BudgetStatus.EXCEEDED:
            raise Exception(f'Budget exceeded: {check.message}')

    def _update_usage_cost(self, request: GenerationRequest, result: GenerationResult) -> None:
        from app.evaluation.cost import CostManager

        est = CostManager.estimate_cost(
            result.model,
            result.provider,
            result.usage.prompt_tokens,
            result.usage.completion_tokens
        )
        result.usage.estimated_cost = est.estimated_cost_usd

        if request.organization_id:
            # We already reserved some budget before the run. To be strictly correct,
            # one would compute the delta, but CostManager doesn't expose a delta method easily
            # without reading _org_daily_spend. For now we just ensure the result has the estimated_cost.
            pass

    async def generate_with_fallback(self, request: GenerationRequest, fallback_model: str | None = None) -> GenerationResult:
        retry_decorator = self._get_retry_decorator()

        self._check_budget_before_run(request, request.model)

        try:
            result = await retry_decorator(self.provider.generate)(request)
            self._update_usage_cost(request, result)
            return result  # type: ignore
        except (LLMTimeoutError, LLMRateLimitError, Exception) as e:
            logger.warning("llm_generation_primary_failed",
                           primary_model=request.model,
                           error=str(e))
                           
            # Try fallback model on primary provider if given
            if fallback_model and fallback_model != request.model:
                try:
                    self._check_budget_before_run(request, fallback_model)
                    fallback_request = request.model_copy(update={"model": fallback_model})
                    result = await retry_decorator(self.provider.generate)(fallback_request)
                    self._update_usage_cost(fallback_request, result)
                    return result  # type: ignore
                except Exception as fb_e:
                    logger.warning("llm_generation_fallback_model_failed", error=str(fb_e))
            
            # Try completely separate fallback provider if configured
            if self.fallback_provider and self.settings.fallback_llm_model:
                logger.error("DEBUG_FALLBACK_PROVIDER_TYPE", type=str(type(self.fallback_provider)))
                logger.info("llm_generation_using_fallback_provider", 
                            provider=self.fallback_provider.name, 
                            model=self.settings.fallback_llm_model)
                try:
                    self._check_budget_before_run(request, self.settings.fallback_llm_model)
                    fallback_request = request.model_copy(update={"model": self.settings.fallback_llm_model})
                    result = await retry_decorator(self.fallback_provider.generate)(fallback_request)
                    self._update_usage_cost(fallback_request, result)
                    return result
                except Exception as fb_p_e:
                    logger.error("llm_generation_fallback_provider_failed", error=str(fb_p_e))
            
            # If all fail, raise the original exception so the domain error reaches the caller
            raise e

    async def generate_structured_with_fallback(
        self,
        request: GenerationRequest,
        schema: type[T],
        fallback_model: str | None = None
    ) -> tuple[GenerationResult, T]:
        retry_decorator = self._get_retry_decorator()

        self._check_budget_before_run(request, request.model)

        try:
            result, parsed = await retry_decorator(self.provider.generate_structured)(request, schema)
            self._update_usage_cost(request, result)
            return result, parsed
        except (LLMTimeoutError, LLMRateLimitError, Exception) as e:
            logger.warning("llm_structured_primary_failed",
                           primary_model=request.model,
                           error=str(e))
                           
            if fallback_model and fallback_model != request.model:
                try:
                    self._check_budget_before_run(request, fallback_model)
                    fallback_request = request.model_copy(update={"model": fallback_model})
                    result, parsed = await retry_decorator(self.provider.generate_structured)(fallback_request, schema)
                    self._update_usage_cost(fallback_request, result)
                    return result, parsed
                except Exception as fb_e:
                    logger.warning("llm_structured_fallback_model_failed", error=str(fb_e))
                    
            if self.fallback_provider and self.settings.fallback_llm_model:
                logger.error("DEBUG_FALLBACK_PROVIDER_TYPE", type=str(type(self.fallback_provider)))
                logger.info("llm_structured_using_fallback_provider", 
                            provider=self.fallback_provider.name, 
                            model=self.settings.fallback_llm_model)
                try:
                    self._check_budget_before_run(request, self.settings.fallback_llm_model)
                    fallback_request = request.model_copy(update={"model": self.settings.fallback_llm_model})
                    result, parsed = await retry_decorator(self.fallback_provider.generate_structured)(fallback_request, schema)
                    self._update_usage_cost(fallback_request, result)
                    return result, parsed
                except Exception as fb_p_e:
                    logger.error("llm_structured_fallback_provider_failed", error=str(fb_p_e))
                    
            raise e

    async def generate(self, request: GenerationRequest) -> GenerationResult:
        """Generate text with configured retry and observability."""
        start_time = time.monotonic()
        log = logger.bind(
            model=request.model,
            provider=self.provider.name,
            task="generate"
        )
        log.debug("starting_llm_generation", messages_count=len(request.messages))

        try:
            result = await self.generate_with_fallback(request)
            latency = time.monotonic() - start_time
            log.info(
                "llm_generation_success",
                prompt_tokens=result.usage.prompt_tokens,
                completion_tokens=result.usage.completion_tokens,
                total_tokens=result.usage.total_tokens,
                estimated_cost=result.usage.estimated_cost,
                latency=latency
            )
            return result
        except Exception as e:
            log.error("llm_generation_failed", error=str(e), error_type=type(e).__name__)
            raise

    async def generate_structured(
        self,
        request: GenerationRequest,
        schema: type[T],
    ) -> tuple[GenerationResult, T]:
        """Generate structured data with configured retry and observability."""
        start_time = time.monotonic()
        log = logger.bind(
            model=request.model,
            provider=self.provider.name,
            schema=schema.__name__,
            task="generate_structured"
        )
        log.debug("starting_llm_structured_generation")

        try:
            result, parsed = await self.generate_structured_with_fallback(request, schema)
            latency = time.monotonic() - start_time
            log.info(
                "llm_structured_generation_success",
                prompt_tokens=result.usage.prompt_tokens,
                completion_tokens=result.usage.completion_tokens,
                total_tokens=result.usage.total_tokens,
                estimated_cost=result.usage.estimated_cost,
                latency=latency
            )
            return result, parsed
        except Exception as e:
            log.error("llm_structured_generation_failed", error=str(e), error_type=type(e).__name__)
            raise

    @retry(
        retry=retry_if_exception_type((LLMTimeoutError, LLMRateLimitError)),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1),
        reraise=True,
    )
    async def stream(self, request: GenerationRequest) -> AsyncGenerator[str, None]:
        """Stream text generation."""
        log = logger.bind(
            model=request.model,
            provider=self.provider.name,
            task="stream"
        )
        log.debug("starting_llm_stream")

        try:
            async for chunk in self.provider.stream(request):
                yield chunk
            log.info("llm_stream_success")
        except Exception as e:
            log.error("llm_stream_failed", error=str(e))
            raise

    async def generate_simple(self, prompt: str, system_prompt: str | None = None) -> str:
        """Helper for simple one-off generation tasks."""
        profile = ModelRouter.classify_task(prompt)
        selection = ModelRouter.route_task(profile)

        messages = []
        if system_prompt:
            messages.append(Message(role="system", content=system_prompt))
        messages.append(Message(role="user", content=prompt))

        request = GenerationRequest(
            messages=messages,
            model=selection.model,
            temperature=self.settings.model_temperature,
            max_tokens=self.settings.model_max_tokens,
        )
        result = await self.generate_with_fallback(request, fallback_model=selection.fallback_model)
        return result.text
