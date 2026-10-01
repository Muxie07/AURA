import httpx, asyncio
async def main():
    async with httpx.AsyncClient(base_url="http://localhost:8000") as client:
        r = await client.get("/health")
        print(r.status_code, r.text)
asyncio.run(main())
