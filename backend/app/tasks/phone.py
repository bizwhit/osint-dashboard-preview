import json
import subprocess
from app.tasks.celery_app import celery_app
from app.utils.audit import log_action
from app.utils.execution import mark_case_complete, mark_case_failed, mark_case_running, save_leads, save_results
from app.utils.normalizers import result
from app.utils.progress import publish
from app.utils.rate_limiter import RateLimitExceeded, enforce
from app.utils.tool_runs import update_tool_run


@celery_app.task(name="app.tasks.phone.run")
def run_phone(case_id: str, phone: str, investigation_id: str | None = None, auto_pivot: bool = True, selected_tools: list | None = None):
    selected_tools = selected_tools or ["phoneinfoga"]
    findings = []; mark_case_running(case_id)
    if "phoneinfoga" in selected_tools:
        try:
            enforce("phoneinfoga"); update_tool_run(case_id, "phoneinfoga", "running"); publish(case_id, "phoneinfoga", "started")
            out = subprocess.run(["phoneinfoga", "scan", "-n", phone, "--json"], capture_output=True, text=True, timeout=300)
            findings.append(result(case_id, "phoneinfoga", phone, "phoneinfoga", None, "medium", json.loads(out.stdout or "{}")))
            update_tool_run(case_id, "phoneinfoga", "completed", 1); publish(case_id, "phoneinfoga", "completed", 1)
        except RateLimitExceeded as exc:
            update_tool_run(case_id, "phoneinfoga", "rate_limited", error=str(exc)); publish(case_id, "phoneinfoga", "rate_limited"); log_action("tool_rate_limited", investigation_id=investigation_id, case_id=case_id, tool="phoneinfoga", metadata={"retry_after": exc.retry_after})
        except Exception as exc:
            update_tool_run(case_id, "phoneinfoga", "failed", error=str(exc)); publish(case_id, "phoneinfoga", "failed")
    try:
        save_results(findings); save_leads(investigation_id, case_id, findings); mark_case_complete(case_id, len(findings)); return {"case_id": case_id, "results_count": len(findings)}
    except Exception as exc:
        mark_case_failed(case_id, str(exc)); raise
