import io
with io.open("backend/tests/conftest.py", "r", encoding="utf-8") as f:
    content = f.read()

override_code = """
    from app.api.deps import get_current_user
    from app.database.models import User
    import uuid
    async def override_get_current_user():
        return User(id=uuid.UUID("00000000-0000-0000-0000-000000000002"), organization_id=uuid.UUID("00000000-0000-0000-0000-000000000001"), role="admin", email="admin@aura.local")
    test_app.dependency_overrides[get_current_user] = override_get_current_user
"""

content = content.replace("test_app.dependency_overrides[get_db_session] = override_get_db", "test_app.dependency_overrides[get_db_session] = override_get_db\n" + override_code)

with io.open("backend/tests/conftest.py", "w", encoding="utf-8") as f:
    f.write(content)
