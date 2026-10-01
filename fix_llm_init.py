with open("backend/app/ai/services/llm.py", "r", encoding="utf-8") as f:
    text = f.read()

import re
replacement = """    def __init__(self) -> None:
        self.settings = get_settings()
        from app.ai.providers.factory import get_llm_provider
        self.provider = get_llm_provider()
        
        self.fallback_provider = None
        if self.settings.fallback_model_provider:
            try:
                self.fallback_provider = get_llm_provider(self.settings.fallback_model_provider)
            except Exception as e:
                import structlog
                structlog.get_logger(__name__).warning("fallback_provider_init_failed", error=str(e))"""

text = re.sub(r'    def __init__\(self\) -> None:.*?if self\.settings\.fallback_model_provider:\n\s*self\.fallback_provider = get_llm_provider\(self\.settings\.fallback_model_provider\)', replacement, text, flags=re.DOTALL)

with open("backend/app/ai/services/llm.py", "w", encoding="utf-8") as f:
    f.write(text)
