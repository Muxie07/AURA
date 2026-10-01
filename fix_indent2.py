import io
with io.open("backend/tests/conftest.py", "r", encoding="utf-8") as f:
    content = f.read()

bad = """
        def override_get_settings():
        return TEST_SETTINGS
    test_app.dependency_overrides[get_settings] = override_get_settings
"""
good = """
    def override_get_settings():
        return TEST_SETTINGS
    test_app.dependency_overrides[get_settings] = override_get_settings
"""
content = content.replace(bad, good)
with io.open("backend/tests/conftest.py", "w", encoding="utf-8") as f:
    f.write(content)
