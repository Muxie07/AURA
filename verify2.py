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

# 4. Evaluations
print("\nEvaluations:")
datasets = api_call("/eval/datasets", token=token)
ds_list = datasets.get("examples", [])
if ds_list:
    ds_id = ds_list[0]["id"]
    eval_run = api_call("/eval/runs", method="POST", data={"dataset_id": ds_id, "model": "mock", "provider": "mock"}, token=token)
    run_id = eval_run["run_id"]
    print("Started Eval:", run_id)
    for i in range(15):
        res = api_call(f"/eval/runs/{run_id}", token=token)
        if res and res["run"]["status"] in ["completed", "failed"]:
            print("Eval Status:", res["run"]["status"])
            print("Eval Pass Rate:", res["run"]["success_rate"])
            print("Eval Results:", len(res["results"]))
            break
        time.sleep(1)

