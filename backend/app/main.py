from fastapi import FastAPI, HTTPException, Query, Request, Depends, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Literal, Optional, List
import asyncio
import uuid
import redis.asyncio as aioredis
from app.config import settings
from app.db import supabase_client
from app.tasks.celery_app import celery_app
from app.utils.tool_registry import TOOLS, tools_for_input_type, validate_selected_tools, all_tool_health
from app.utils.tool_runs import create_tool_runs
from app.utils.audit import log_action
from app.utils.admin_auth import require_admin
from app.utils.rate_limiter import RateLimitExceeded, enforce_investigation

app = FastAPI(title="OSINT Unified API")
app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:3000"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])
redis_client = aioredis.from_url(settings.redis_url, decode_responses=True)


class SearchRequest(BaseModel):
    query: str
    input_type: Literal["username", "email", "phone", "domain"]
    investigation_id: Optional[str] = None
    auto_pivot: bool = True
    consent_accepted: bool = False
    selected_tools: Optional[List[str]] = None
    wmn_tags: Optional[List[str]] = None


def require_db():
    if not supabase_client: raise HTTPException(status_code=503, detail="Supabase is not configured.")


def request_ip(request: Request) -> str:
    return request.headers.get("x-forwarded-for", "").split(",")[0].strip() or (request.client.host if request.client else "unknown")


@app.get("/health")
async def health(): return {"status": "ok", "service": "osint-api"}


@app.get("/api/tools")
async def list_tools(input_type: Optional[str] = Query(None)):
    if input_type and input_type not in {"username", "email", "phone", "domain"}: raise HTTPException(status_code=400, detail="Unsupported input type.")
    return [tool.__dict__ for tool in (tools_for_input_type(input_type) if input_type else list(TOOLS.values()))]


@app.get("/api/tools/health", dependencies=[Depends(require_admin)])
async def tool_health(): return await all_tool_health()


@app.post("/api/search")
async def create_search(body: SearchRequest, request: Request):
    require_db(); ip = request_ip(request)
    if not body.consent_accepted:
        log_action("search_rejected_no_consent", input_type=body.input_type, query=body.query, client_ip=ip)
        raise HTTPException(status_code=403, detail="Authorized-use consent is required.")
    try: selected = validate_selected_tools(body.input_type, body.selected_tools)
    except ValueError as exc: raise HTTPException(status_code=400, detail=str(exc))
    if not selected: raise HTTPException(status_code=400, detail="Select at least one tool.")
    investigation_id = body.investigation_id or str(uuid.uuid4())
    try: enforce_investigation(investigation_id)
    except RateLimitExceeded as exc:
        log_action("search_rate_limited", investigation_id=investigation_id, input_type=body.input_type, query=body.query, client_ip=ip, metadata={"retry_after": exc.retry_after})
        raise HTTPException(status_code=429, detail=str(exc), headers={"Retry-After": str(exc.retry_after)})
    case_id = str(uuid.uuid4())
    if not body.investigation_id:
        supabase_client.table("investigations").insert({"id": investigation_id, "name": f"{body.input_type}: {body.query}", "consent_accepted": True, "consent_ip": ip}).execute()
    supabase_client.table("cases").insert({"id": case_id, "investigation_id": investigation_id, "input_type": body.input_type, "query": body.query, "status": "queued", "selected_tools": selected, "auto_pivot_enabled": body.auto_pivot, "wmn_tags": body.wmn_tags or []}).execute()
    create_tool_runs(case_id, selected)
    task = {"username": "app.tasks.username.run", "email": "app.tasks.email.run", "phone": "app.tasks.phone.run", "domain": "app.tasks.domain.run"}[body.input_type]
    kwargs = {"investigation_id": investigation_id, "auto_pivot": body.auto_pivot, "selected_tools": selected}
    if body.input_type == "username": kwargs["wmn_tags"] = body.wmn_tags or []
    celery_app.send_task(task, args=[case_id, body.query], kwargs=kwargs)
    log_action("search_requested", investigation_id=investigation_id, case_id=case_id, input_type=body.input_type, query=body.query, consent_accepted=True, client_ip=ip, metadata={"selected_tools": selected, "auto_pivot": body.auto_pivot, "wmn_tags": body.wmn_tags or []})
    return {"case_id": case_id, "investigation_id": investigation_id, "status": "queued"}


@app.get("/api/case/{case_id}")
async def get_case(case_id: str):
    require_db(); rows = supabase_client.table("cases").select("*").eq("id", case_id).execute().data
    if not rows: raise HTTPException(status_code=404, detail="Case not found.")
    return {**rows[0], "results": supabase_client.table("search_results").select("*").eq("case_id", case_id).execute().data}


@app.get("/api/case/{case_id}/tool-runs")
async def get_tool_runs(case_id: str):
    require_db(); return supabase_client.table("tool_runs").select("*").eq("case_id", case_id).order("created_at").execute().data


@app.get("/api/investigations")
async def investigations():
    require_db(); return supabase_client.table("investigations").select("*").order("created_at", desc=True).execute().data


@app.get("/api/audit", dependencies=[Depends(require_admin)])
async def audit(limit: int = Query(100, le=500)):
    require_db(); return supabase_client.table("audit_logs").select("*").order("created_at", desc=True).limit(limit).execute().data


@app.websocket("/ws/progress/{case_id}")
async def case_progress(websocket: WebSocket, case_id: str):
    await websocket.accept(); pubsub = redis_client.pubsub(); await pubsub.subscribe(f"case:{case_id}")
    try:
        while True:
            message = await pubsub.get_message(ignore_subscribe_messages=True, timeout=1)
            if message and message.get("type") == "message": await websocket.send_text(message["data"])
            await asyncio.sleep(0.25)
    except WebSocketDisconnect: pass
    finally:
        await pubsub.unsubscribe(f"case:{case_id}"); await pubsub.close()
