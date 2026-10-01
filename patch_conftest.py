with open("backend/tests/conftest.py", "r", encoding="utf-8") as f:
    text = f.read()

patch_code = """
    # Override the database dependency
    async def override_get_db():
        yield db_session

    test_app.dependency_overrides[get_db_session] = override_get_db

    # Patch get_session_factory globally for tests
    import app.database.base as db_base
    from unittest.mock import MagicMock
    mock_factory = MagicMock()
    mock_factory.return_value = db_session
    db_base.get_session_factory = lambda: lambda: db_session
"""

if "test_app.dependency_overrides[get_db_session] = override_get_db" in text:
    text = text.replace("""    # Override the database dependency
    async def override_get_db():
        yield db_session

    test_app.dependency_overrides[get_db_session] = override_get_db""", patch_code)
    
    with open("backend/tests/conftest.py", "w", encoding="utf-8") as f:
        f.write(text)
    print("Patched conftest.py!")
else:
    print("Could not find block")
