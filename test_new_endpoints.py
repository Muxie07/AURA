import httpx
import asyncio

async def test():
    # Login
    async with httpx.AsyncClient(base_url="http://localhost:8000") as client:
        r = await client.post("/api/v1/auth/token", json={"email": "demo@aura-sre.com", "password": "demo1234"})
        if r.status_code != 200:
            print("Login failed", r.text)
            return
        token = r.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        
        # Test Settings
        r = await client.get("/api/v1/settings", headers=headers)
        print("Settings:", r.status_code, r.text[:100])
        
        # Test Forecasting
        r = await client.get("/api/v1/forecasting", headers=headers)
        print("Forecasting:", r.status_code, r.text[:100])
        
        # Test Datasets
        r = await client.get("/api/v1/eval/datasets", headers=headers)
        print("Datasets:", r.status_code, r.text[:100])
        
        # Test Benchmarks
        r = await client.get("/api/v1/eval/benchmarks", headers=headers)
        print("Benchmarks:", r.status_code, r.text[:100])

asyncio.run(test())
