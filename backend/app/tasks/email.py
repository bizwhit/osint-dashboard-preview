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
    try:
        if "holehe" in selected_tools:
            try:
                enforce("holehe"); update_tool_run(case_id, "holehe", "running"); publish(case_id, "holehe", "started")
                out = subprocess.run(["holehe", email, "--json"], capture_output=True, text=True, timeout=300)
                rows = [result(case_id, "holehe", email, a.get("name"), a.get("url"), "high", {"raw": a}) for a in json.loads(out.stdout or "{}").get("accounts", [])]
                findings.extend(rows); update_tool_run(case_id, "holehe", "completed", len(rows)); publish(case_id, "holehe", "completed", len(rows))
            except RateLimitExceeded as exc:
                update_tool_run(case_id, "holehe", "rate_limited", error=str(exc)); publish(case_id, "holehe", "rate_limited"); log_action("tool_rate_limited", investigation_id=investigation_id, case_id=case_id, tool="holehe", metadata={"retry_after": exc.retry_after})
            except Exception as exc:
                update_tool_run(case_id, "holehe", "failed", error=str(exc)); publish(case_id, "holehe", "failed")
        if "theharvester" in selected_tools:
            try:
                enforce("theharvester"); update_tool_run(case_id, "theharvester", "running"); publish(case_id, "theharvester", "started")
                domain, path = email.split("@", 1)[1], f"/app/reports/{case_id}-harvester"
                subprocess.run(["theHarvester", "-d", domain, "-b", "google,bing", "-f", path], capture_output=True, text=True, timeout=300)
                report = json.loads(open(f"{path}.json", encoding="utf-8").read())
                rows = [result(case_id, "theharvester", email, "email_discovery", None, "medium", {"associated_email": value}) for value in report.get("emails", [])]
                findings.extend(rows); update_tool_run(case_id, "theharvester", "completed", len(rows)); publish(case_id, "theharvester", "completed", len(rows))
            except RateLimitExceeded as exc:
                update_tool_run(case_id, "theharvester", "rate_limited", error=str(exc)); publish(case_id, "theharvester", "rate_limited"); log_action("tool_rate_limited", investigation_id=investigation_id, case_id=case_id, tool="theharvester", metadata={"retry_after": exc.retry_after})
            except Exception as exc:
                update_tool_run(case_id, "theharvester", "failed", error=str(exc)); publish(case_id, "theharvester", "failed")
        save_results(findings); save_leads(investigation_id, case_id, findings); mark_case_complete(case_id, len(findings)); return {"case_id": case_id, "results_count": len(findings)}
    except Exception as exc:
        mark_case_failed(case_id, str(exc)); raise
