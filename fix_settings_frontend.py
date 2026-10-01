path = "frontend/src/app/settings/page.tsx"
with open(path, "r", encoding="utf-8") as f:
    text = f.read()
text = text.replace("fetchApi('/settings/')", "fetchApi('/settings')")
with open(path, "w", encoding="utf-8") as f:
    f.write(text)
print("Fixed frontend fetch")
