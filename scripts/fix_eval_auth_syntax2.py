import re
import os

filepath = r"backend/app/api/v1/eval.py"

with open(filepath, "r", encoding="utf-8") as f:
    content = f.read()

# Fix the parameter order
content = content.replace(
    "async def get_benchmarks(task_type: str | None = None, current_user: CurrentUserDep)",
    "async def get_benchmarks(current_user: CurrentUserDep, task_type: str | None = None)"
)

content = content.replace(
    "async def get_datasets(category: str | None = None, current_user: CurrentUserDep)",
    "async def get_datasets(current_user: CurrentUserDep, category: str | None = None)"
)

# For get_incidents, limit: int = 50 is at the end, which is fine since current_user has no default.
# But let's make sure it's valid: async def get_incidents(organization_id: uuid.UUID, current_user: CurrentUserDep, limit: int = 50) -> dict[str, Any]:
# That is valid.

with open(filepath, "w", encoding="utf-8") as f:
    f.write(content)
print("eval.py fixed syntax 2 successfully")
