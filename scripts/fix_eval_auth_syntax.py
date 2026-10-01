import re
import os

filepath = r"backend/app/api/v1/eval.py"

with open(filepath, "r", encoding="utf-8") as f:
    content = f.read()

content = content.replace("), current_user: CurrentUserDep)", ", current_user: CurrentUserDep)")

with open(filepath, "w", encoding="utf-8") as f:
    f.write(content)
print("eval.py fixed syntax successfully")
