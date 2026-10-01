import sys

path = "frontend/src/app/evaluations/page.tsx"
with open(path, "rb") as f:
    b = f.read()

# Decode with replacement to strip/fix any invalid bytes
text = b.decode("utf-8", errors="replace")

# Replace the unicode replacement character if it exists
text = text.replace("\ufffd", "")

with open(path, "wb") as f:
    f.write(text.encode("utf-8"))

print("Encoding fixed!")
