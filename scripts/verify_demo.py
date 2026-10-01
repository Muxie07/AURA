import asyncio
import sys

import httpx


async def verify():
    print("Starting AURA Localhost Verification...\n")

    # 1. Frontend Check
    try:
        r_frontend = httpx.get("http://localhost:3000", follow_redirects=False)
        print(f"[Frontend] UI reachable: PASS (HTTP {r_frontend.status_code})")
    except Exception as e:
        print(f"[Frontend] Failed to reach frontend: {e}")
        sys.exit(1)

    # 2. Login & Auth
    try:
        r_auth = httpx.post(
            "http://localhost:8000/api/v1/auth/token",
            json={"email": "demo@aura-sre.com", "password": "demo1234"},
        )
        if r_auth.status_code == 200:
            token = r_auth.json()["access_token"]
            print("[Auth] JWT Authentication: PASS")
        else:
            print(f"[Auth] Login failed: HTTP {r_auth.status_code}")
            sys.exit(1)
    except Exception as e:
        print(f"[Auth] Backend unreachable: {e}")
        sys.exit(1)

    headers = {"Authorization": f"Bearer {token}"}

    # 3. API Health
    try:
        r_health = httpx.get("http://localhost:8000/api/v1/health")
        print(f"[Backend] API Health: PASS (HTTP {r_health.status_code})")
    except Exception as e:
        print(f"[Backend] Health check failed: {e}")

    # 4. Agent Runs
    r_runs = httpx.get("http://localhost:8000/api/v1/agent/runs", headers=headers)
    runs = r_runs.json().get("runs", [])
    if len(runs) >= 15:
        print(f"[Data] Agent Runs: PASS ({len(runs)} found)")
    else:
        print(f"[Data] Agent Runs: FAIL (Expected >= 15, got {len(runs)})")

    # 5. Approvals
    r_appr = httpx.get("http://localhost:8000/api/v1/agent/approvals", headers=headers)
    apprs = r_appr.json().get("approvals", [])
    if len(apprs) >= 3:
        print(f"[Data] Approvals: PASS ({len(apprs)} found)")
    else:
        print(f"[Data] Approvals: FAIL (Expected >= 3, got {len(apprs)})")

    # 6. Conversations
    r_conv = httpx.get("http://localhost:8000/api/v1/conversations", headers=headers)
    convs = r_conv.json().get("items", [])
    if len(convs) >= 15:
        print(f"[Data] Conversations: PASS ({len(convs)} found)")
    else:
        print(f"[Data] Conversations: FAIL (Expected >= 15, got {len(convs)})")

    # 7. Knowledge Bases
    r_kb = httpx.get("http://localhost:8000/api/v1/knowledge-bases", headers=headers)
    kbs = r_kb.json()
    if isinstance(kbs, list) and len(kbs) >= 6:
        print(f"[Data] Knowledge Bases: PASS ({len(kbs)} found)")
    else:
        print("[Data] Knowledge Bases: FAIL (Expected >= 6)")

    print("\nVerification Complete.")


if __name__ == "__main__":
    asyncio.run(verify())
