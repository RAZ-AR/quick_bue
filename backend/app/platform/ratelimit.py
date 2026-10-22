"""Fixed-window counters in Redis for endpoints that cost money or can be abused (sending e-mail).

Fails open: if Redis is down the request goes through, the per-e-mail limit in the database still applies.
"""

import logging

from redis import asyncio as aioredis
from redis.exceptions import RedisError

from app.config import get_settings

log = logging.getLogger(__name__)
_client: aioredis.Redis | None = None


def _redis() -> aioredis.Redis:
    global _client
    if _client is None:
        _client = aioredis.from_url(get_settings().redis_url, socket_timeout=1, socket_connect_timeout=1)
    return _client


async def hit(key: str, limit: int, window_s: int) -> bool:
    """Count one hit; False once `limit` hits happened within the current window."""
    try:
        r = _redis()
        n = await r.incr(f"rl:{key}")
        if n == 1:
            await r.expire(f"rl:{key}", window_s)
        return n <= limit
    except (RedisError, OSError) as e:
        log.warning("rate limit unavailable (%s), letting %s through", e, key)
        return True
