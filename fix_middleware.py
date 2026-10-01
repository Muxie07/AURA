with open("backend/app/observability/middleware.py", "r", encoding="utf-8") as f:
    text = f.read()

import re

old_log = """
        # Structured access log
        logger.info(
            "http_request",
            status_code=response.status_code,
            duration_ms=elapsed_ms,
            client_host=request.client.host if request.client else "unknown",
            user_agent=request.headers.get("user-agent", ""),
        )
"""
new_log = """
        # Structured access log
        logger.info(
            "http_request",
            status_code=response.status_code,
            duration_ms=elapsed_ms,
            client_host=request.client.host if request.client else "unknown",
            user_agent=request.headers.get("user-agent", ""),
        )

        # Push observability data to Redis if authenticated
        org_id = getattr(request.state, "organization_id", None)
        if org_id:
            import json
            from datetime import datetime, timezone
            import asyncio
            from app.security.rate_limit import get_redis_client
            
            metric = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "method": request.method,
                "path": request.url.path,
                "status_code": response.status_code,
                "duration_ms": elapsed_ms,
                "tenant_id": org_id,
                "request_id": request_id
            }
            
            async def push_metric(m):
                try:
                    redis = await get_redis_client()
                    key = f"observability:metrics:{org_id}"
                    await redis.lpush(key, json.dumps(m))
                    await redis.ltrim(key, 0, 9999)  # Keep last 10,000 requests
                except Exception:
                    pass
            
            asyncio.create_task(push_metric(metric))
"""
text = text.replace(old_log.strip(), new_log.strip())

with open("backend/app/observability/middleware.py", "w", encoding="utf-8") as f:
    f.write(text)
