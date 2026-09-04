import json
import subprocess
from app.tasks.celery_app import celery_app
from app.utils.normalizers import result


@celery_app.task(name="app.tasks.email.run")
def run_email(case_id: str, email: str, selected_tools: list | None = None):
    selected_tools = selected_tools or ["holehe", "theharvester"]
    findings = []
    if "holehe" in selected_tools:
        try:
            out = subprocess.run(["holehe", email, "--json"], capture_output=True, text=True, timeout=300)
            for account in json.loads(out.stdout or "{}").get("accounts", []):
                findings.append(result(case_id, "holehe", email, account.get("name"), account.get("url"), "high"))
        except Exception:
            pass
    if "theharvester" in selected_tools:
        try:
            domain = email.split("@", 1)[1]
            path = f"/app/reports/{case_id}-harvester"
            subprocess.run(["theHarvester", "-d", domain, "-b", "google,bing", "-f", path], capture_output=True, text=True, timeout=300)
            report = json.loads(open(f"{path}.json", encoding="utf-8").read())
            for found in report.get("emails", []):
                findings.append(result(case_id, "theharvester", email, "email_discovery", None, "medium", {"associated_email": found}))
        except Exception:
            pass
    return findings
