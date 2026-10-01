import time

import redis.asyncio as aioredis
from fastapi import HTTPException, Request
from starlette.status import HTTP_429_TOO_MANY_REQUESTS

from app.config.settings import get_settings

# Global Redis client for rate limiting
_redis_client: aioredis.Redis | None = None


async def get_redis_client() -> aioredis.Redis:
    global _redis_client
    if _redis_client is None:
        settings = get_settings()
        _redis_client = aioredis.from_url(settings.redis_url)
    return _redis_client


async def rate_limit_dependency(request: Request) -> None:
    """
    Sliding window rate limit dependency.
    """
    settings = get_settings()
    client = await get_redis_client()

    # In a real multi-tenant app, we'd use the organization ID or user ID.
    # For now, fallback to client IP if no user is found.
    # If the app has auth, `request.state.user` might be present.
    client_id = request.client.host if request.client else "unknown"
    if hasattr(request.state, "user"):
        client_id = str(request.state.user.id)

    key = f"rate_limit:ai_generate:{client_id}"

    now = time.time()
    window = settings.aura_rate_limit_window_seconds
    limit = settings.aura_rate_limit_requests

    # Using Redis ZSET for sliding window
    async with client.pipeline(transaction=True) as pipe:
        # Remove requests older than the current window
        pipe.zremrangebyscore(key, 0, now - window)
        # Add the current request
        pipe.zadd(key, {str(now): now})
        # Count requests in the window
        pipe.zcard(key)
        # Set expiry to clean up old keys
        pipe.expire(key, window)

        results = await pipe.execute()

    request_count = results[2]

    if request_count > limit:
        raise HTTPException(
            status_code=HTTP_429_TOO_MANY_REQUESTS,
            detail="Too Many Requests",
            headers={"Retry-After": str(window)},
        )
