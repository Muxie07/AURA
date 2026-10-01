import io
import re

with io.open("backend/app/api/v1/conversations.py", "r", encoding="utf-8") as f:
    content = f.read()

# Fix repeated arguments
content = re.sub(r",\s*current_user:\s*CurrentUserDep\s*,\s*current_user:\s*CurrentUserDep", ", current_user: CurrentUserDep", content)
content = re.sub(r"db:\s*DatabaseDep\s*,\s*current_user:\s*CurrentUserDep\s*,\s*current_user:\s*CurrentUserDep", "db: DatabaseDep, current_user: CurrentUserDep", content)
content = re.sub(r", current_user: CurrentUserDep\)\s*->\s*PaginatedResponse\[MessageResponse\]:", ")\n    -> PaginatedResponse[MessageResponse]:", content)

with io.open("backend/app/api/v1/conversations.py", "w", encoding="utf-8") as f:
    f.write(content)
