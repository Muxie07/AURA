import httpx
import uuid
import json

c = httpx.Client(base_url="http://localhost:8000")
# we don't have a token, so we can't test it directly unless we mock it or login.
# Wait, I created a seed script earlier with user demo@aura-sre.com demo1234
r = c.post("/api/v1/auth/token", json={"email": "demo@aura-sre.com", "password": "demo1234"})
if not r.is_success:
    print("Login failed", r.text)
    exit(1)

token = r.json()["access_token"]
c.headers["Authorization"] = f"Bearer {token}"

# get a conversation
r = c.post("/api/v1/conversations", json={"title": "Test Stream"})
if not r.is_success:
    print("Conv failed", r.text)
    exit(1)
conv_id = r.json()["id"]

# post a run
r = c.post("/api/v1/runs", json={"conversation_id": conv_id, "request": "test"})
if not r.is_success:
    print("Run failed", r.text)
    exit(1)

run_id = r.json()["run_id"]
print("Run created:", run_id)

# now stream
with c.stream("GET", f"/api/v1/runs/{run_id}/stream") as response:
    print("Stream status:", response.status_code)
    print("Stream headers:", response.headers)
    for line in response.iter_lines():
        if line:
            print(line)
        
