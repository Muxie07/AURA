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
        
        # Find quotation dataset
        ds = next(d for d in datasets if "Quotation" in d["name"])
        
        # Run eval
        print(f"Triggering eval for {ds['name']}...")
        r = await client.post("/api/v1/eval/runs", json={"dataset_id": ds["id"], "model": "gemini-1.5-pro", "provider": "gemini"}, headers=headers)
        print(r.status_code, r.text)

asyncio.run(test())
