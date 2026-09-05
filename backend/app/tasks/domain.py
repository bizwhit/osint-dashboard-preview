import asyncio
import subprocess
from app.tasks.celery_app import celery_app
from app.utils.audit import log_action
from app.utils.execution import mark_case_complete, mark_case_failed, mark_case_running, save_leads, save_results
from app.utils.normalizers import result
from app.utils.progress import publish
from app.utils.rate_limiter import RateLimitExceeded, enforce
from app.utils.spiderfoot_client import run_domain_scan
from app.utils.tool_runs import update_tool_run


@celery_app.task(name="app.tasks.domain.run")
def run_domain(case_id: str, domain: str, investigation_id: str | None = None, auto_pivot: bool = True, selected_tools: list | None = None):
    selected_tools = selected_tools or ["spiderfoot", "theharvester"]
    findings = []; mark_case_running(case_id)
    if "spiderfoot" in selected_tools:
        try:
            enforce("spiderfoot"); update_tool_run(case_id, "spiderfoot", "running"); publish(case_id, "spiderfoot", "started")
            rows = [result(case_id, "spiderfoot", domain, item["type"], item["data"], "medium", {"module": item["module"]}) for item in asyncio.run(run_domain_scan(domain))]
            findings.extend(rows); update_tool_run(case_id, "spiderfoot", "completed", len(rows)); publish(case_id, "spiderfoot", "completed", len(rows))
        except RateLimitExceeded as exc:
            update_tool_run(case_id, "spiderfoot", "rate_limited", error=str(exc)); publish(case_id, "spiderfoot", "rate_limited"); log_action("tool_rate_limited", investigation_id=investigation_id, case_id=case_id, tool="spiderfoot", metadata={"retry_after": exc.retry_after})
        except Exception as exc:
            update_tool_run(case_id, "spiderfoot", "failed", error=str(exc)); publish(case_id, "spiderfoot", "failed")
    if "theharvester" in selected_tools:
        try:
            enforce("theharvester"); update_tool_run(case_id, "theharvester", "running"); publish(case_id, "theharvester", "started")
            subprocess.run(["theHarvester", "-d", domain, "-b", "google,bing"], capture_output=True, text=True, timeout=300)
            update_tool_run(case_id, "theharvester", "completed", 0); publish(case_id, "theharvester", "completed", 0)
        except RateLimitExceeded as exc:
            update_tool_run(case_id, "theharvester", "rate_limited", error=str(exc)); publish(case_id, "theharvester", "rate_limited"); log_action("tool_rate_limited", investigation_id=investigation_id, case_id=case_id, tool="theharvester", metadata={"retry_after": exc.retry_after})
        except Exception as exc:
            update_tool_run(case_id, "theharvester", "failed", error=str(exc)); publish(case_id, "theharvester", "failed")
    try:
        save_results(findings); save_leads(investigation_id, case_id, findings); mark_case_complete(case_id, len(findings)); return {"case_id": case_id, "results_count": len(findings)}
    except Exception as exc:
        mark_case_failed(case_id, str(exc)); raise
