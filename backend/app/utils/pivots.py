"""One-hop child cases; the unique database index arbitrates concurrent inserts."""
import uuid
from postgrest.exceptions import APIError
from app.db import supabase_client
from app.tasks.celery_app import celery_app
from app.utils.tool_registry import tools_for_input_type
from app.utils.tool_runs import create_tool_runs

TASKS = {'username': 'app.tasks.username.run', 'email': 'app.tasks.email.run', 'phone': 'app.tasks.phone.run'}


def create_child_case(investigation_id: str | None, parent_case_id: str, source_tool: str, lead: dict) -> str | None:
    if not investigation_id or not supabase_client:
        return None
    input_type = lead.get('lead_type')
    value = str(lead.get('value', '')).strip()
    if input_type not in TASKS or not value:
        return None
    parents = supabase_client.table('cases').select('investigation_id,parent_case_id,auto_pivot_enabled').eq('id', parent_case_id).execute().data
    if not parents:
        return None
    parent = parents[0]
    if parent['investigation_id'] != investigation_id or parent.get('parent_case_id') or not parent.get('auto_pivot_enabled'):
        return None
    existing = supabase_client.table('cases').select('id').eq('investigation_id', investigation_id).eq('input_type', input_type).eq('query', value).execute().data
    if existing:
        return None
    selected = [tool.id for tool in tools_for_input_type(input_type) if tool.default_enabled]
    child_id = str(uuid.uuid4())
    try:
        supabase_client.table('cases').insert({
            'id': child_id, 'investigation_id': investigation_id, 'input_type': input_type, 'query': value,
            'status': 'queued', 'selected_tools': selected, 'auto_pivot_enabled': False,
            'discovered_via': f'{source_tool}:{parent_case_id}', 'parent_case_id': parent_case_id,
        }).execute()
    except APIError as exc:
        if str(exc.code) == '23505':
            return None
        raise
    try:
        create_tool_runs(child_id, selected)
        celery_app.send_task(TASKS[input_type], args=[child_id, value], kwargs={
            'investigation_id': investigation_id, 'auto_pivot': False, 'selected_tools': selected})
    except Exception:
        supabase_client.table('cases').update({'status': 'failed'}).eq('id', child_id).execute()
        raise
    return child_id
