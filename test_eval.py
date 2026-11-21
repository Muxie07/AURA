import httpx
import asyncio

async def main():
    async with httpx.AsyncClient(base_url="http://localhost:8000") as client:
        # Login
        r = await client.post("/api/v1/auth/token", json={"email": "demo@aura-sre.com", "password": "demo1234"})
        if r.status_code != 200:
            print("Auth failed", r.status_code, r.text)
            return
        
        token = r.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        
        # Test datasets
        r_ds = await client.get("/api/v1/eval/datasets", headers=headers)
        print("Datasets:", r_ds.status_code, r_ds.text[:200])

        # Test benchmarks
        r_bm = await client.get("/api/v1/eval/benchmarks", headers=headers)
        print("Benchmarks:", r_bm.status_code, r_bm.text[:200])

asyncio.run(main())
