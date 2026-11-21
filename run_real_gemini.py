import httpx
import asyncio
import time

async def run():
    async with httpx.AsyncClient(base_url="http://localhost:8000") as client:
        r = await client.post("/api/v1/auth/token", json={"email": "demo@aura-sre.com", "password": "demo1234"})
        token = r.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        
        # Get datasets
        r = await client.get("/api/v1/eval/datasets", headers=headers)
        datasets = r.json()["examples"]
        # Find Quotation Golden Dataset
        ds = next(d for d in datasets if "Quotation" in d["name"])
        
        print(f"Triggering real Gemini eval for dataset: {ds['name']} ({ds['id']})")
        r = await client.post("/api/v1/eval/runs", json={
            "dataset_id": ds["id"], 
            "model": "gemini-1.5-pro", 
            "provider": "google"
        }, headers=headers)
        
        run_id = r.json()["run_id"]
        print("Run created:", run_id)
        
        # Poll for completion
        for _ in range(60):
            r2 = await client.get(f"/api/v1/eval/runs/{run_id}", headers=headers)
            run = r2.json()["run"]
            print(f"Polling... sample_count={run['sample_count']}")
            if run['sample_count'] > 0:
                print("\nFINISHED!")
                print(f"Samples: {run['sample_count']}")
                print(f"Success Rate: {run['success_rate']}")
                print(f"Latency: {run['avg_latency_ms']} ms")
                break
            time.sleep(2)

asyncio.run(run())
