import urllib.request
import json
import time

base_url = "http://localhost:8000/api/v1"

def api_call(path, method="GET", data=None, token=None):
    headers = {"Content-Type": "application/json"}
    if token: headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(f"{base_url}{path}", method=method, headers=headers)
    if data: req.data = json.dumps(data).encode()
    try:
        with urllib.request.urlopen(req) as res:
            return json.loads(res.read().decode())
    except urllib.error.HTTPError as e:
        print(f"Error {e.code} on {path}: {e.read().decode()}")
        return None

token_data = api_call("/auth/token", method="POST", data={"email": "demo@aura-sre.com", "password": "demo1234"})
token = token_data["access_token"]
print("Auth Token:", bool(token))

conv = api_call("/conversations", method="POST", data={"title": "Demo Quotation Verify"}, token=token)
conv_id = conv["id"]

prompts = [
    "Search for Acme Technologies",
    "Find products related to industrial systems",
    "Calculate pricing for PROD-X with quantity 1",
    "Create a draft quotation for Acme Technologies using 1 of PROD-X"
]

for prompt in prompts:
    print(f"\nPrompt: {prompt}")
    run = api_call("/runs", method="POST", data={"conversation_id": conv_id, "request": prompt, "model": "mock", "provider": "mock"}, token=token)
    if not run: continue
    run_id = run["run_id"]
    for i in range(15):
        status_res = api_call(f"/runs/{run_id}", token=token)
        if status_res and status_res["status"] in ["completed", "failed"]:
            print("Status:", status_res["status"])
            break
        time.sleep(2)

print("\nVerify Quotations in DB...")
