import asyncio
import json
import subprocess
import uuid
from datetime import datetime
from app.db import supabase_client
from app.tasks.celery_app import celery_app
from app.utils.audit import log_action
from app.utils.execution import mark_case_complete, mark_case_failed, mark_case_running, save_leads, save_results
from app.utils.normalizers import result
from app.utils.progress import publish
from app.utils.rate_limiter import RateLimitExceeded, enforce
from app.utils.tool_runs import update_tool_run
from app.utils.whatsmyname_client import search as wmn_search


def stamp() -> str:
    return datetime.utcnow().isoformat()


def child_search(investigation_id: str, parent_case_id: str, lead: dict) -> None:
    if not supabase_client:
        return
    tasks = {
        "username": "app.tasks.username.run",
        "email": "app.tasks.email.run",
        "phone": "app.tasks.phone.run",
    }
    task = tasks.get(lead["lead_type"])
    if not task:
        return
    child_id = str(uuid.uuid4())
    supabase_client.table("cases").insert({
        "id": child_id, "investigation_id": investigation_id, "input_type": lead["lead_type"],
        "query": lead["value"], "status": "queued", "selected_tools": [],
        "auto_pivot_enabled": False, "discovered_via": f"username:{parent_case_id}", "parent_case_id": parent_case_id,
    }).execute()
    celery_app.send_task(task, args=[child_id, lead["value"]], kwargs={"investigation_id": investigation_id, "auto_pivot": False})


@celery_app.task(name="app.tasks.username.run")
def run_username(case_id: str, username: str, investigation_id: str | None = None, auto_pivot: bool = True, selected_tools: list | None = None, wmn_tags: list | None = None):
    selected_tools = selected_tools or ["sherlock", "maigret", "whatsmyname"]
    findings = []
    mark_case_running(case_id)

    def run_sherlock():
        try:
            enforce("sherlock"); update_tool_run(case_id, "sherlock", "running"); publish(case_id, "sherlock", "started")
            out = subprocess.run(["sherlock", username, "--json"], capture_output=True, text=True, timeout=300)
            rows = [result(case_id, "sherlock", username, site, data.get("url"), "high") for site, data in json.loads(out.stdout or "{}").items()]
            update_tool_run(case_id, "sherlock", "completed", len(rows)); publish(case_id, "sherlock", "completed", len(rows)); return rows
        except RateLimitExceeded as exc:
            update_tool_run(case_id, "sherlock", "rate_limited", error=str(exc)); publish(case_id, "sherlock", "rate_limited"); log_action("tool_rate_limited", investigation_id=investigation_id, case_id=case_id, tool="sherlock", metadata={"retry_after": exc.retry_after}); return []
        except Exception as exc:
            update_tool_run(case_id, "sherlock", "failed", error=str(exc)); publish(case_id, "sherlock", "failed"); return []

    def run_maigret():
        try:
            enforce("maigret"); update_tool_run(case_id, "maigret", "running"); publish(case_id, "maigret", "started")
            path = f"/app/reports/{case_id}-maigret"
            out = subprocess.run(["maigret", username, "--json", "--no-progressbar", "-o", path], capture_output=True, text=True, timeout=600)
            rows = []
            if out.returncode == 0:
                report = json.loads(open(f"{path}.json", encoding="utf-8").read())
                for site, data in report.get("sites", {}).items():
                    if data.get("status") == "claimed":
                        rows.append(result(case_id, "maigret", username, site, data.get("url"), "high", {"profile": data.get("status", {})}))
            update_tool_run(case_id, "maigret", "completed", len(rows)); publish(case_id, "maigret", "completed", len(rows)); return rows
        except RateLimitExceeded as exc:
            update_tool_run(case_id, "maigret", "rate_limited", error=str(exc)); publish(case_id, "maigret", "rate_limited"); log_action("tool_rate_limited", investigation_id=investigation_id, case_id=case_id, tool="maigret", metadata={"retry_after": exc.retry_after}); return []
        except Exception as exc:
            update_tool_run(case_id, "maigret", "failed", error=str(exc)); publish(case_id, "maigret", "failed"); return []

    def run_wmn():
        try:
            enforce("whatsmyname"); update_tool_run(case_id, "whatsmyname", "running"); publish(case_id, "whatsmyname", "started")
            known = {str(row["site"]).lower() for row in findings if row.get("site")}
            rows = [result(case_id, "whatsmyname", username, hit["site"], hit["url"], "medium", {"category": hit["category"]}) for hit in asyncio.run(wmn_search(username, wmn_tags)) if hit["site"].lower() not in known]
            update_tool_run(case_id, "whatsmyname", "completed", len(rows)); publish(case_id, "whatsmyname", "completed", len(rows)); return rows
        except RateLimitExceeded as exc:
            update_tool_run(case_id, "whatsmyname", "rate_limited", error=str(exc)); publish(case_id, "whatsmyname", "rate_limited"); log_action("tool_rate_limited", investigation_id=investigation_id, case_id=case_id, tool="whatsmyname", metadata={"retry_after": exc.retry_after}); return []
        except Exception as exc:
            update_tool_run(case_id, "whatsmyname", "failed", error=str(exc)); publish(case_id, "whatsmyname", "failed"); return []

    try:
        if "sherlock" in selected_tools: findings.extend(run_sherlock())
        if "maigret" in selected_tools: findings.extend(run_maigret())
        if "whatsmyname" in selected_tools: findings.extend(run_wmn())
        save_results(findings)
        leads = save_leads(investigation_id, case_id, findings)
        if auto_pivot:
            for lead in leads: child_search(investigation_id, case_id, lead)
        mark_case_complete(case_id, len(findings))
        return {"case_id": case_id, "results_count": len(findings)}
    except Exception as exc:
        mark_case_failed(case_id, str(exc)); raise
