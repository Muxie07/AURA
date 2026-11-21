import httpx
import asyncio
import time

async def test():
    async with httpx.AsyncClient(base_url="http://localhost:8000") as client:
        r = await client.post("/api/v1/auth/token", json={"email": "demo@aura-sre.com", "password": "demo1234"})
        token = r.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        
        r2 = await client.get(f"/api/v1/eval/runs/ee71a1f0-721b-4733-895b-0a06d58ee1ab", headers=headers)
        run = r2.json()["run"]
        print(f"Sample count: {run['sample_count']}")
        if run['sample_count'] > 0:
            print("Success rate:", run["success_rate"])

asyncio.run(test())
