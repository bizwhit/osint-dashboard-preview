import json
import redis
from app.config import settings


def publish(case_id: str, tool: str, status: str, count: int = 0) -> None:
    redis.from_url(settings.redis_url, decode_responses=True).publish(f'case:{case_id}', json.dumps({'case_id': case_id, 'tool': tool, 'status': status, 'results_count': count}))
