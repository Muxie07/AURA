import io
with io.open("backend/tests/conftest.py", "r", encoding="utf-8") as f:
    content = f.read()

content = content.replace("from app.config.settings import get_settings\n", "")

with io.open("backend/tests/conftest.py", "w", encoding="utf-8") as f:
    f.write(content)
