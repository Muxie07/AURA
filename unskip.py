import io

with io.open("backend/tests/test_ai_endpoints.py", "r", encoding="utf-8") as f:
    content = f.read()
content = content.replace("@pytest.mark.skip(reason='Docker unavailable')\nasync def test_ai_generate", "async def test_ai_generate")
with io.open("backend/tests/test_ai_endpoints.py", "w", encoding="utf-8") as f:
    f.write(content)

with io.open("backend/tests/test_phase9_security.py", "r", encoding="utf-8") as f:
    content = f.read()
content = content.replace("@pytest.mark.skip(reason='Docker unavailable')\nasync def test_rate_limiting", "async def test_rate_limiting")
with io.open("backend/tests/test_phase9_security.py", "w", encoding="utf-8") as f:
    f.write(content)
