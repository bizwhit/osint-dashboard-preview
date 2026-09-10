"""Controlled one-hop pivot creation shared by worker tasks."""
import uuid
from app.db import supabase_client
from app.tasks.celery_app import celery_app
from app.utils.tool_registry import tools_for_input_type
from app.utils.tool_runs import create_tool_runs

TASKS = {
    "username": "app.tasks.username.run",
    "email": "app.tasks.email.run",
    "phone": "app.tasks.phone.run",
}


def create_child_case(investigation_id: str | None, parent_case_id: str, source_tool: str, lead: dict) -> str | None:
    if not investigation_id or not supabase_client:
        return None
    input_type = lead.get("lead_type")
    value = str(lead.get("value", "")).strip()
    if input_type not in TASKS or not value:
        return None
    existing = supabase_client.table("cases").select("id").eq("investigation_id", investigation_id).eq("input_type", input_type).eq("query", value).execute().data
    if existing:
        return None
    selected_tools = [tool.id for tool in tools_for_input_type(input_type) if tool.default_enabled]
    child_id = str(uuid.uuid4())
    supabase_client.table("cases").insert({
        "id": child_id, "investigation_id": investigation_id, "input_type": input_type, "query": value,
        "status": "queued", "selected_tools": selected_tools, "auto_pivot_enabled": False,
        "discovered_via": f"{source_tool}:{parent_case_id}", "parent_case_id": parent_case_id,
    }).execute()
    create_tool_runs(child_id, selected_tools)
    celery_app.send_task(TASKS[input_type], args=[child_id, value], kwargs={"investigation_id": investigation_id, "auto_pivot": False, "selected_tools": selected_tools})
    return child_id
