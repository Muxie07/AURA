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
        
        # Test runs
        r_runs = await client.get("/api/v1/runs", headers=headers)
        print("Runs:", r_runs.status_code, r_runs.text[:200])

        # Test approvals
        r_app = await client.get("/api/v1/approvals", headers=headers)
        print("Approvals:", r_app.status_code, r_app.text[:200])

        # Test health
        r_health = await client.get("/health")
        print("Health:", r_health.status_code, r_health.text[:200])

asyncio.run(main())
