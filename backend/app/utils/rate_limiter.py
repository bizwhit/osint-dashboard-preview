import time
import redis
from app.config import settings

LIMITS = {'sherlock': (10, 60), 'maigret': (6, 60), 'whatsmyname': (5, 60), 'holehe': (15, 60), 'theharvester': (10, 60), 'phoneinfoga': (15, 60), 'spiderfoot': (4, 60)}


class RateLimitExceeded(Exception):
    pass


def enforce(tool: str) -> None:
    limit, window = LIMITS[tool]
    client = redis.from_url(settings.redis_url, decode_responses=True)
    key, now = f'ratelimit:{tool}', time.time()
    client.zremrangebyscore(key, 0, now - window)
    if client.zcard(key) >= limit:
        raise RateLimitExceeded(f'{tool} rate limit exceeded')
    client.zadd(key, {str(now): now})
    client.expire(key, window * 2)
