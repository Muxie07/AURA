import io
import re
with io.open("backend/app/api/v1/conversations.py", "r", encoding="utf-8") as f:
    content = f.read()

content = re.sub(r"current_user:\s*CurrentUserDep\s*=\s*Depends\(\),?", "current_user: CurrentUserDep", content)

with io.open("backend/app/api/v1/conversations.py", "w", encoding="utf-8") as f:
    f.write(content)
