import asyncio
import json
import subprocess
from app.tasks.celery_app import celery_app
from app.utils.normalizers import result
from app.utils.spiderfoot_client import run_domain_scan


@celery_app.task(name="app.tasks.domain.run")
def run_domain(case_id: str, domain: str, selected_tools: list | None = None):
    selected_tools = selected_tools or ["spiderfoot", "theharvester"]
    findings = []
    if "spiderfoot" in selected_tools:
        try:
            for event in asyncio.run(run_domain_scan(domain)):
                findings.append(result(case_id, "spiderfoot", domain, event["type"], event["data"], "medium", {"module": event["module"]}))
        except Exception:
            pass
    if "theharvester" in selected_tools:
        try:
            path = f"/app/reports/{case_id}-domain"
            subprocess.run(["theHarvester", "-d", domain, "-b", "google,bing", "-f", path], capture_output=True, text=True, timeout=300)
            report = json.loads(open(f"{path}.json", encoding="utf-8").read())
            for email in report.get("emails", []):
                findings.append(result(case_id, "theharvester", domain, "email_enumeration", None, "medium", {"associated_email": email}))
            for host in report.get("hosts", []):
                findings.append(result(case_id, "theharvester", domain, "subdomain", host, "medium", {"subdomain": host}))
        except Exception:
            pass
    return findings
