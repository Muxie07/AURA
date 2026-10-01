path = "frontend/src/app/lib/api.ts"
with open(path, "r", encoding="utf-8") as f:
    text = f.read()

hack = """  // Normalize endpoints where frontend components incorrectly include the /agent namespace
  if (endpoint.startsWith('/agent/')) {
    endpoint = endpoint.replace('/agent/', '/');
  }"""

text = text.replace(hack, "")

with open(path, "w", encoding="utf-8") as f:
    f.write(text)
print("Removed API hack")
