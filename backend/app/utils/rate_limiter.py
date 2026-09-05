import time
import redis
from app.config import settings

LIMITS = {
    "sherlock": (10, 60), "maigret": (6, 60), "whatsmyname": (5, 60),
    "holehe": (15, 60), "theharvester": (10, 60), "phoneinfoga": (15, 60),
    "spiderfoot": (4, 60),
}
INVESTIGATION_LIMIT = (30, 3600)


class RateLimitExceeded(Exception):
    def __init__(self, scope: str, retry_after: int):
        self.scope = scope
        self.retry_after = retry_after
        super().__init__(f"{scope} rate limit exceeded; retry after {retry_after}s")


def _enforce(key: str, max_calls: int, window: int) -> None:
    client = redis.from_url(settings.redis_url, decode_responses=True)
    current = time.time()
    client.zremrangebyscore(key, 0, current - window)
    if client.zcard(key) >= max_calls:
        oldest = client.zrange(key, 0, 0, withscores=True)
        retry = int(max(1, (oldest[0][1] + window - current) if oldest else window))
        raise RateLimitExceeded(key, retry)
    client.zadd(key, {str(current): current})
    client.expire(key, window * 2)


def enforce(tool: str) -> None:
    max_calls, window = LIMITS[tool]
    _enforce(f"ratelimit:tool:{tool}", max_calls, window)


def enforce_investigation(investigation_id: str) -> None:
    max_calls, window = INVESTIGATION_LIMIT
    _enforce(f"ratelimit:investigation:{investigation_id}", max_calls, window)
