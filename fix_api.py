with open("frontend/src/app/lib/api.ts", "r", encoding="utf-8") as f:
    text = f.read()

replacement = """export async function fetchApi(endpoint: string, options: RequestInit = {}): Promise<Response> {
  // Normalize endpoints where frontend components incorrectly include the /agent namespace
  if (endpoint.startsWith('/agent/')) {
    endpoint = endpoint.replace('/agent/', '/');
  }
"""

text = text.replace(
    "export async function fetchApi(endpoint: string, options: RequestInit = {}): Promise<Response> {",
    replacement
)

with open("frontend/src/app/lib/api.ts", "w", encoding="utf-8") as f:
    f.write(text)
print("Fixed api.ts")
