import httpx
import asyncio
import time

async def test():
    async with httpx.AsyncClient(base_url="http://localhost:8000") as client:
        r = await client.post("/api/v1/auth/token", json={"email": "demo@aura-sre.com", "password": "demo1234"})
        token = r.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        
        r2 = await client.get(f"/api/v1/eval/runs/28a9be62-7a5c-4bac-86d6-2213a9e2031c", headers=headers)
        run = r2.json()["run"]
        print(f"Sample count: {run['sample_count']}")
        if run['sample_count'] > 0:
            print("Success rate:", run["success_rate"])
            print("Latency:", run["avg_latency_ms"])

asyncio.run(test())
