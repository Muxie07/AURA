with open("backend/tests/conftest.py", "r", encoding="utf-8") as f:
    text = f.read()

import re
old_env = """
    os.environ["MODEL_PROVIDER"] = "mock"
    os.environ["MODEL_NAME"] = "mock"
"""

new_env = """
    os.environ["PRIMARY_LLM_PROVIDER"] = "mock"
    os.environ["PRIMARY_LLM_MODEL"] = "mock"
    os.environ["FALLBACK_LLM_PROVIDER"] = "mock"
    os.environ["FALLBACK_LLM_MODEL"] = "mock"
"""

text = text.replace(old_env.strip(), new_env.strip())

with open("backend/tests/conftest.py", "w", encoding="utf-8") as f:
    f.write(text)
