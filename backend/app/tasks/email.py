import json
import subprocess
from app.tasks.celery_app import celery_app
from app.utils.audit import log_action
from app.utils.execution import mark_case_complete, mark_case_failed, mark_case_running, save_leads, save_results
from app.utils.normalizers import result
from app.utils.progress import publish
from app.utils.rate_limiter import RateLimitExceeded, enforce
from app.utils.tool_runs import update_tool_run


@celery_app.task(name="app.tasks.email.run")
def run_email(case_id: str, email: str, investigation_id: str | None = None, auto_pivot: bool = True, selected_tools: list | None = None):
    selected_tools = selected_tools or ["holehe", "theharvester"]
    findings = []; mark_case_running(case_id)
    for tool, command in [("holehe", ["holehe", email, "--json"]), ("theharvester", ["theHarvester", "-d", email.split("@", 1)[1], "-b", "google,bing", "-f", f"/app/reports/{case_id}-harvester"])]:
        if tool not in selected_tools: continue
        try:
            enforce(tool); update_tool_run(case_id, tool, "running"); publish(case_id, tool, "started")
            out = subprocess.run(command, capture_output=True, text=True, timeout=300)
            payload = json.loads(out.stdout or "{}") if tool == "holehe" else {}
            rows = [result(case_id, tool, email, item.get("name"), item.get("url"), "high", {"raw": item}) for item in payload.get("accounts", [])]
            findings.extend(rows); update_tool_run(case_id, tool, "completed", len(rows)); publish(case_id, tool, "completed", len(rows))
        except RateLimitExceeded as exc:
            update_tool_run(case_id, tool, "rate_limited", error=str(exc)); publish(case_id, tool, "rate_limited"); log_action("tool_rate_limited", investigation_id=investigation_id, case_id=case_id, tool=tool, metadata={"retry_after": exc.retry_after})
        except Exception as exc:
            update_tool_run(case_id, tool, "failed", error=str(exc)); publish(case_id, tool, "failed")
    try:
        save_results(findings); save_leads(investigation_id, case_id, findings); mark_case_complete(case_id, len(findings)); return {"case_id": case_id, "results_count": len(findings)}
    except Exception as exc:
        mark_case_failed(case_id, str(exc)); raise
