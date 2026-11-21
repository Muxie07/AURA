import httpx
import asyncio

async def run():
    async with httpx.AsyncClient(base_url="http://localhost:8000") as client:
        r = await client.post("/api/v1/auth/token", json={"email": "demo@aura-sre.com", "password": "demo1234"})
        token = r.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        
        r = await client.get("/api/v1/eval/runs", headers=headers)
        runs = r.json()["runs"]
        latest = runs[0]
        print("Run ID:", latest["id"])
        print("Model:", latest["model"])
        print("Sample count:", latest["sample_count"])
        print("Success rate:", latest["success_rate"])
        print("Latency:", latest["avg_latency_ms"])

asyncio.run(run())
