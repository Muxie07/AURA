with open("backend/app/ai/services/llm.py", "r", encoding="utf-8") as f:
    text = f.read()

import re

# Update __init__
init_replacement = """    def __init__(self) -> None:
        self.settings = get_settings()
        from app.ai.providers.factory import get_llm_provider
        self.provider = get_llm_provider()
        
        self.fallback_provider = None
        if self.settings.fallback_model_provider:
            self.fallback_provider = get_llm_provider(self.settings.fallback_model_provider)"""

text = re.sub(r'    def __init__\(self\) -> None:\n        self\.settings = get_settings\(\)\n        from app\.ai\.providers\.factory import get_llm_provider\n        self\.provider = get_llm_provider\(\)', init_replacement, text)

# Update generate_with_fallback
generate_replacement = """    async def generate_with_fallback(self, request: GenerationRequest, fallback_model: str | None = None) -> GenerationResult:
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
            if self.fallback_provider and self.settings.fallback_model_name:
                logger.info("llm_generation_using_fallback_provider", 
                            provider=self.fallback_provider.name, 
                            model=self.settings.fallback_model_name)
                try:
                    self._check_budget_before_run(request, self.settings.fallback_model_name)
                    fallback_request = request.model_copy(update={"model": self.settings.fallback_model_name})
                    result = await retry_decorator(self.fallback_provider.generate)(fallback_request)
                    self._update_usage_cost(fallback_request, result)
                    return result
                except Exception as fb_p_e:
                    logger.error("llm_generation_fallback_provider_failed", error=str(fb_p_e))
            
            # If all fail, raise clear error
            raise RuntimeError(f"All LLM providers failed. Primary error: {str(e)}") from e"""

text = re.sub(r'    async def generate_with_fallback\(self, request: GenerationRequest, fallback_model: str \| None = None\) -> GenerationResult:(.*?)(?=    async def generate_structured_with_fallback)', generate_replacement + "\n\n", text, flags=re.DOTALL)


# Update generate_structured_with_fallback
structured_replacement = """    async def generate_structured_with_fallback(
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
                    
            if self.fallback_provider and self.settings.fallback_model_name:
                logger.info("llm_structured_using_fallback_provider", 
                            provider=self.fallback_provider.name, 
                            model=self.settings.fallback_model_name)
                try:
                    self._check_budget_before_run(request, self.settings.fallback_model_name)
                    fallback_request = request.model_copy(update={"model": self.settings.fallback_model_name})
                    result, parsed = await retry_decorator(self.fallback_provider.generate_structured)(fallback_request, schema)
                    self._update_usage_cost(fallback_request, result)
                    return result, parsed
                except Exception as fb_p_e:
                    logger.error("llm_structured_fallback_provider_failed", error=str(fb_p_e))
                    
            raise RuntimeError(f"All LLM structured providers failed. Primary error: {str(e)}") from e"""

text = re.sub(r'    async def generate_structured_with_fallback\((.*?)(?=    async def generate\()', structured_replacement + "\n\n", text, flags=re.DOTALL)

with open("backend/app/ai/services/llm.py", "w", encoding="utf-8") as f:
    f.write(text)
