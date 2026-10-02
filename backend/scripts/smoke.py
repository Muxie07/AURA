import argparse
import asyncio
import sys

import httpx


async def main():
    base_url = "http://localhost:8000"

    # Preflight Check
    try:
        r = httpx.options(
            f"{base_url}/api/v1/conversations",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "authorization,content-type"
            },
            timeout=5.0
        )
        if r.status_code not in (200, 204):
            print(f"❌ CORS preflight failed: {r.status_code}")
            sys.exit(1)
        if "access-control-allow-origin" not in r.headers:
            print("❌ CORS preflight missing allow-origin header")
            sys.exit(1)
        print("✅ CORS preflight passed")
    except Exception as e:
        print(f"❌ CORS preflight error: {e}")
        sys.exit(1)
    parser = argparse.ArgumentParser()
    parser.add_argument("--env", default="development")
    args = parser.parse_args()

    base_url = "http://localhost:8000"

    # 1. Health check (retries while stack warms)
    print("Checking /health...")
    for _ in range(10):
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(f"{base_url}/health", timeout=5.0)
                if resp.status_code == 200:
                    break
        except Exception:
            pass
        await asyncio.sleep(2)
    else:
        print("Failed to reach /health")
        sys.exit(1)

    print("Checking /ready...")
    async with httpx.AsyncClient() as client:
        resp = await client.get(f"{base_url}/ready", timeout=10.0)
        if resp.status_code != 200:
            print("Failed /ready")
            sys.exit(1)

    print("Smoke test passed (stubbed).")

if __name__ == "__main__":
    asyncio.run(main())
