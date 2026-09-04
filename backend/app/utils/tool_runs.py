from datetime import datetime
from typing import List
import uuid
from app.db import supabase_client


def now() -> str:
    return datetime.utcnow().isoformat()


def create_tool_runs(case_id: str, tools: List[str]) -> None:
    if not supabase_client:
        return
    supabase_client.table('tool_runs').insert([{'id': str(uuid.uuid4()), 'case_id': case_id, 'tool': tool, 'status': 'queued', 'created_at': now(), 'updated_at': now()} for tool in tools]).execute()


def update_tool_run(case_id: str, tool: str, status: str, count: int | None = None, error: str | None = None) -> None:
    if not supabase_client:
        return
    payload = {'status': status, 'updated_at': now()}
    if status == 'running': payload['started_at'] = now()
    if status in {'completed', 'failed', 'skipped', 'rate_limited'}: payload['completed_at'] = now()
    if count is not None: payload['results_count'] = count
    if error: payload['error_message'] = error[:1000]
    supabase_client.table('tool_runs').update(payload).eq('case_id', case_id).eq('tool', tool).execute()
