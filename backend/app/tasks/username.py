import asyncio
import json
import subprocess
from app.tasks.celery_app import celery_app
from app.utils.audit import log_action
from app.utils.execution import mark_case_complete, mark_case_failed, mark_case_running, save_leads, save_results
from app.utils.normalizers import result
from app.utils.pivots import create_child_case
from app.utils.progress import publish
from app.utils.rate_limiter import RateLimitExceeded, enforce
from app.utils.tool_runs import update_tool_run
from app.utils.whatsmyname_client import search as wmn_search


@celery_app.task(name="app.tasks.username.run")
def run_username(case_id: str, username: str, investigation_id: str | None = None, auto_pivot: bool = True, selected_tools: list | None = None, wmn_tags: list | None = None):
    selected_tools = selected_tools or ["sherlock", "maigret", "whatsmyname"]
    findings = []
    mark_case_running(case_id)

    def execute(tool: str, operation):
        try:
            enforce(tool); update_tool_run(case_id, tool, "running"); publish(case_id, tool, "started")
            rows = operation()
            update_tool_run(case_id, tool, "completed", len(rows)); publish(case_id, tool, "completed", len(rows)); return rows
        except RateLimitExceeded as exc:
            update_tool_run(case_id, tool, "rate_limited", error=str(exc)); publish(case_id, tool, "rate_limited")
            log_action("tool_rate_limited", investigation_id=investigation_id, case_id=case_id, tool=tool, metadata={"retry_after": exc.retry_after}); return []
        except Exception as exc:
            update_tool_run(case_id, tool, "failed", error=str(exc)); publish(case_id, tool, "failed"); return []

    def sherlock():
        out = subprocess.run(["sherlock", username, "--json"], capture_output=True, text=True, timeout=300)
        data = json.loads(out.stdout or "{}")
        return [result(case_id, "sherlock", username, site, row.get("url"), "high") for site, row in data.items()]

    def maigret():
        path = f"/app/reports/{case_id}-maigret"
        out = subprocess.run(["maigret", username, "--json", "--no-progressbar", "-o", path], capture_output=True, text=True, timeout=600)
        if out.returncode != 0: return []
        report = json.loads(open(f"{path}.json", encoding="utf-8").read())
        return [result(case_id, "maigret", username, site, row.get("url"), "high", {"profile": row.get("status", {})}) for site, row in report.get("sites", {}).items() if row.get("status") == "claimed"]

    def whatsmyname():
        known = {str(row["site"]).lower() for row in findings if row.get("site")}
        return [result(case_id, "whatsmyname", username, hit["site"], hit["url"], "medium", {"category": hit["category"]}) for hit in asyncio.run(wmn_search(username, wmn_tags)) if hit["site"].lower() not in known]

    try:
        if "sherlock" in selected_tools: findings.extend(execute("sherlock", sherlock))
        if "maigret" in selected_tools: findings.extend(execute("maigret", maigret))
        if "whatsmyname" in selected_tools: findings.extend(execute("whatsmyname", whatsmyname))
        save_results(findings)
        leads = save_leads(investigation_id, case_id, findings)
        if auto_pivot:
            for lead in leads: create_child_case(investigation_id, case_id, "username", lead)
        mark_case_complete(case_id, len(findings))
        return {"case_id": case_id, "results_count": len(findings)}
    except Exception as exc:
        mark_case_failed(case_id, str(exc)); raise
