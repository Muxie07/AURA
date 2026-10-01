path = "backend/app/api/v1/settings.py"
with open(path, "r", encoding="utf-8") as f:
    text = f.read()
text = text.replace('@router.get("/")', '@router.get("")')
text = text.replace('@router.patch("/")', '@router.patch("")')
with open(path, "w", encoding="utf-8") as f:
    f.write(text)
print("Fixed router slashes")
