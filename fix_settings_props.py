path = "backend/app/api/v1/settings.py"
with open(path, "r", encoding="utf-8") as f:
    text = f.read()

text = text.replace('app_settings.llm_provider', 'app_settings.primary_llm_provider')
text = text.replace('app_settings.aura_model', 'app_settings.primary_llm_model')
text = text.replace('app_settings.aura_fallback_model', 'app_settings.fallback_llm_model')
text = text.replace('app_settings.aura_embedding_model', 'app_settings.embedding_model')
text = text.replace('app_settings.aura_temperature', 'app_settings.model_temperature')

with open(path, "w", encoding="utf-8") as f:
    f.write(text)
print("Fixed props")
