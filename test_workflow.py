import urllib.request
import json

base_url = "http://localhost:8000/api/v1"

req = urllib.request.Request(f"{base_url}/auth/token", method="POST", data=json.dumps({"email": "demo@aura-sre.com", "password": "demo1234"}).encode(), headers={"Content-Type": "application/json"})
with urllib.request.urlopen(req) as res:
    token = json.loads(res.read().decode())["access_token"]
print("Got token:", token[:10])

req = urllib.request.Request(f"{base_url}/conversations", method="POST", data=json.dumps({"title": "Test"}).encode(), headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"})
with urllib.request.urlopen(req) as res:
    conv_id = json.loads(res.read().decode())["id"]
print("Got conversation:", conv_id)

req = urllib.request.Request(f"{base_url}/runs", method="POST", data=json.dumps({"conversation_id": conv_id, "request": "Search for Acme Technologies"}).encode(), headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"})
with urllib.request.urlopen(req) as res:
    run_id = json.loads(res.read().decode())["run_id"]
print("Got run:", run_id)
