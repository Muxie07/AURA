import httpx
import asyncio

async def test():
    async with httpx.AsyncClient(base_url="http://localhost:8000") as client:
        r = await client.post("/api/v1/auth/token", json={"email": "demo@aura-sre.com", "password": "demo1234"})
        token = r.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        
        print("GET Settings")
        r = await client.get("/api/v1/settings", headers=headers)
        print(r.status_code, r.json())
        
        print("\nPATCH Settings")
        r = await client.patch("/api/v1/settings", json={"temperature": 0.8}, headers=headers)
        print(r.status_code, r.json())
        
        print("\nGET Settings again")
        r = await client.get("/api/v1/settings", headers=headers)
        print(r.status_code, r.json())

asyncio.run(test())
