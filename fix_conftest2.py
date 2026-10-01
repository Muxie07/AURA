with open("backend/tests/conftest.py", "r", encoding="utf-8") as f:
    text = f.read()

import re
old_env = """
    os.environ["FALLBACK_LLM_MODEL"] = "mock"
"""
new_env = """
    os.environ["FALLBACK_LLM_MODEL"] = "mock"
    
    from app.config.settings import get_settings
    get_settings.cache_clear()
"""

text = text.replace(old_env.strip(), new_env.strip())

with open("backend/tests/conftest.py", "w", encoding="utf-8") as f:
    f.write(text)
