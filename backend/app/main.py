from fastapi import FastAPI, HTTPException, Query, Request, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Literal, Optional, List
import uuid
from app.db import supabase_client
from app.tasks.celery_app import celery_app
from app.utils.tool_registry import TOOLS, tools_for_input_type, validate_selected_tools, all_tool_health
from app.utils.tool_runs import create_tool_runs
from app.utils.audit import log_action
from app.utils.admin_auth import require_admin

app = FastAPI(title='OSINT Unified API')
app.add_middleware(CORSMiddleware, allow_origins=['http://localhost:3000'], allow_credentials=True, allow_methods=['*'], allow_headers=['*'])


class SearchRequest(BaseModel):
    query: str
    input_type: Literal['username', 'email', 'phone', 'domain']
    investigation_id: Optional[str] = None
    auto_pivot: bool = True
    consent_accepted: bool = False
    selected_tools: Optional[List[str]] = None
    wmn_tags: Optional[List[str]] = None


def require_db():
    if not supabase_client:
        raise HTTPException(status_code=503, detail='Supabase is not configured.')


@app.get('/health')
async def health():
    return {'status': 'ok', 'service': 'osint-api'}


@app.get('/api/tools')
async def list_tools(input_type: Optional[str] = Query(None)):
    tools = tools_for_input_type(input_type) if input_type else list(TOOLS.values())
    return [tool.__dict__ for tool in tools]


@app.get('/api/tools/health', dependencies=[Depends(require_admin)])
async def tool_health():
    return await all_tool_health()


@app.post('/api/search')
async def create_search(body: SearchRequest, request: Request):
    require_db()
    if not body.consent_accepted:
        log_action('search_rejected_no_consent', input_type=body.input_type, query=body.query)
        raise HTTPException(status_code=403, detail='Authorized-use consent is required.')
    try:
        selected = validate_selected_tools(body.input_type, body.selected_tools)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    if not selected:
        raise HTTPException(status_code=400, detail='Select at least one tool.')
    investigation_id = body.investigation_id or str(uuid.uuid4())
    case_id = str(uuid.uuid4())
    if not body.investigation_id:
        supabase_client.table('investigations').insert({'id': investigation_id, 'name': f'{body.input_type}: {body.query}', 'consent_accepted': True}).execute()
    supabase_client.table('cases').insert({'id': case_id, 'investigation_id': investigation_id, 'input_type': body.input_type, 'query': body.query, 'selected_tools': selected, 'auto_pivot_enabled': body.auto_pivot, 'wmn_tags': body.wmn_tags or []}).execute()
    create_tool_runs(case_id, selected)
    task = {'username': 'app.tasks.username.run', 'email': 'app.tasks.email.run', 'phone': 'app.tasks.phone.run', 'domain': 'app.tasks.domain.run'}[body.input_type]
    celery_app.send_task(task, args=[case_id, body.query], kwargs={'selected_tools': selected, 'wmn_tags': body.wmn_tags or []} if body.input_type == 'username' else {'selected_tools': selected})
    log_action('search_requested', investigation_id=investigation_id, case_id=case_id, input_type=body.input_type, query=body.query, consent_accepted=True, metadata={'selected_tools': selected, 'auto_pivot': body.auto_pivot})
    return {'case_id': case_id, 'investigation_id': investigation_id, 'status': 'queued'}


@app.get('/api/case/{case_id}')
async def get_case(case_id: str):
    require_db()
    case = supabase_client.table('cases').select('*').eq('id', case_id).execute().data
    if not case: raise HTTPException(status_code=404, detail='Case not found.')
    results = supabase_client.table('search_results').select('*').eq('case_id', case_id).execute().data
    return {**case[0], 'results': results}


@app.get('/api/case/{case_id}/tool-runs')
async def get_tool_runs(case_id: str):
    require_db()
    rows = supabase_client.table('tool_runs').select('*').eq('case_id', case_id).order('created_at').execute().data
    return rows


@app.get('/api/investigations')
async def investigations():
    require_db()
    return supabase_client.table('investigations').select('*').order('created_at', desc=True).execute().data


@app.get('/api/audit', dependencies=[Depends(require_admin)])
async def audit(limit: int = Query(100, le=500)):
    require_db()
    return supabase_client.table('audit_logs').select('*').order('created_at', desc=True).limit(limit).execute().data
