import httpx
import asyncio

async def test():
    async with httpx.AsyncClient(base_url="http://localhost:8000") as client:
        r = await client.post("/api/v1/auth/token", json={"email": "demo@aura-sre.com", "password": "demo1234"})
        token = r.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        
        # Get datasets
        r = await client.get("/api/v1/eval/datasets", headers=headers)
        datasets = r.json()["examples"]
        ds = datasets[0]
        
        r = await client.post("/api/v1/eval/runs", json={"dataset_id": ds["id"], "model": "mock", "provider": "mock"}, headers=headers)
        run_id = r.json()["run_id"]
        print("Run created:", run_id)

asyncio.run(test())
