import io
import re

with io.open("backend/tests/conftest.py", "r", encoding="utf-8") as f:
    content = f.read()

cleanup = """
@pytest.fixture(autouse=True)
async def cleanup_redis():
    yield
    from app.security.rate_limit import _redis_client
    import app.security.rate_limit as rl
    if rl._redis_client is not None:
        try:
            await rl._redis_client.aclose()
        except:
            pass
        rl._redis_client = None
"""
if "def cleanup_redis" not in content:
    content = content + "\n" + cleanup
    with io.open("backend/tests/conftest.py", "w", encoding="utf-8") as f:
        f.write(content)
