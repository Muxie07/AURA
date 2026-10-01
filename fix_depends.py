import io
with io.open("backend/app/api/v1/conversations.py", "r", encoding="utf-8") as f:
    content = f.read()

content = content.replace("current_user: CurrentUserDep = Depends()", "current_user: CurrentUserDep")

with io.open("backend/app/api/v1/conversations.py", "w", encoding="utf-8") as f:
    f.write(content)
