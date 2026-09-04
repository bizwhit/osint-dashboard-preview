import asyncio
import json
import subprocess
from app.tasks.celery_app import celery_app
from app.utils.normalizers import result
from app.utils.whatsmyname_client import search as wmn_search


@celery_app.task(name="app.tasks.username.run")
def run_username(case_id: str, username: str, selected_tools: list | None = None, wmn_tags: list | None = None):
    selected_tools = selected_tools or ["sherlock", "maigret", "whatsmyname"]
    findings = []
    if "sherlock" in selected_tools:
        try:
            out = subprocess.run(["sherlock", username, "--json"], capture_output=True, text=True, timeout=300)
            for site, data in json.loads(out.stdout or "{}").items():
                findings.append(result(case_id, "sherlock", username, site, data.get("url"), "high"))
        except Exception:
            pass
    if "maigret" in selected_tools:
        try:
            path = f"/app/reports/{case_id}-maigret"
            out = subprocess.run(["maigret", username, "--json", "--no-progressbar", "-o", path], capture_output=True, text=True, timeout=600)
            if out.returncode == 0:
                report = json.loads(open(f"{path}.json", encoding="utf-8").read())
                for site, data in report.get("sites", {}).items():
                    if data.get("status") == "claimed":
                        findings.append(result(case_id, "maigret", username, site, data.get("url"), "high", {"status": data.get("status")}))
        except Exception:
            pass
    if "whatsmyname" in selected_tools:
        try:
            known = {str(row["site"]).lower() for row in findings if row.get("site")}
            for hit in asyncio.run(wmn_search(username, wmn_tags)):
                if hit["site"].lower() not in known:
                    findings.append(result(case_id, "whatsmyname", username, hit["site"], hit["url"], "medium", {"category": hit["category"]}))
        except Exception:
            pass
    return findings
