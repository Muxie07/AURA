import re

path = "backend/app/api/v1/eval.py"
with open(path, "r", encoding="utf-8") as f:
    text = f.read()

# Fix the input_prompt assignment
text = text.replace("input_prompt=ex.input,", "input_prompt=ex.input.replace('\\x00', '\\\\x00'),")

with open(path, "w", encoding="utf-8") as f:
    f.write(text)

print("Fixed null byte issue.")
