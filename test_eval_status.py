import httpx
import asyncio

async def test():
    async with httpx.AsyncClient(base_url="http://localhost:8000") as client:
        r = await client.post("/api/v1/auth/token", json={"email": "demo@aura-sre.com", "password": "demo1234"})
        token = r.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        
        # Get runs
        r = await client.get("/api/v1/eval/runs", headers=headers)
        print("Runs:", r.json())
        
        runs = r.json()["runs"]
        if runs:
            r2 = await client.get(f"/api/v1/eval/runs/{runs[0]['id']}", headers=headers)
            print("Run Details:", r2.json())

asyncio.run(test())
