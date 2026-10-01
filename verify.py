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

# 1. Login
token_data = api_call("/auth/token", method="POST", data={"email": "demo@aura-sre.com", "password": "demo1234"})
token = token_data["access_token"]
print("Auth:", bool(token))

# 2. Settings
settings = api_call("/settings", token=token)
orig_temp = settings["environment"].get("llm_temperature", 0.7)
api_call("/settings", method="PATCH", data={"settings": {"default_temperature": 0.9}}, token=token)
updated_settings = api_call("/settings", token=token)
print("Settings Update:", updated_settings["environment"].get("llm_temperature") == 0.9)
api_call("/settings", method="PATCH", data={"settings": {"default_temperature": orig_temp}}, token=token)

# 3. Conversations (Test 1)
conv = api_call("/conversations", method="POST", data={"title": "Demo Verify"}, token=token)
conv_id = conv["id"]
runs_to_test = [
    "Search for Acme Technologies",
    "Find products related to industrial pumps",
    "Create a draft quotation for Acme Technologies with 1 Enterprise Database Server (PROD-X)",
    "Show me recent API latency"
]

for prompt in runs_to_test:
    print(f"\nPrompt: {prompt}")
    run = api_call("/runs", method="POST", data={"conversation_id": conv_id, "request": prompt}, token=token)
    if not run: continue
    run_id = run["run_id"]
    for i in range(15):
        status_res = api_call(f"/runs/{run_id}", token=token)
        if status_res and status_res["status"] in ["completed", "failed"]:
            print("Status:", status_res["status"])
            print("Final Response:", status_res.get("final_response", "")[:100])
            break
        time.sleep(2)

# 4. Evaluations
print("\nEvaluations:")
datasets = api_call("/eval/datasets", token=token)
if datasets and datasets.get("datasets"):
    ds_id = datasets["datasets"][0]["id"]
    eval_run = api_call("/eval/runs", method="POST", data={"dataset_id": ds_id, "model": "mock", "provider": "mock"}, token=token)
    run_id = eval_run["run_id"]
    for i in range(10):
        res = api_call(f"/eval/runs/{run_id}", token=token)
        if res and res["run"]["status"] in ["completed", "failed"]:
            print("Eval Status:", res["run"]["status"])
            print("Eval Pass Rate:", res["run"]["success_rate"])
            break
        time.sleep(1)

# 5. Forecasting
forecast = api_call("/forecasting/", token=token)
print("\nForecasting Has Data:", forecast.get("has_sufficient_data"))
