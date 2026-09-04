import json
import subprocess
from app.tasks.celery_app import celery_app
from app.utils.normalizers import result


@celery_app.task(name="app.tasks.phone.run")
def run_phone(case_id: str, phone: str, selected_tools: list | None = None):
    selected_tools = selected_tools or ["phoneinfoga"]
    if "phoneinfoga" not in selected_tools:
        return []
    try:
        out = subprocess.run(["phoneinfoga", "scan", "-n", phone, "--json"], capture_output=True, text=True, timeout=300)
        data = json.loads(out.stdout or "{}")
        return [result(case_id, "phoneinfoga", phone, "phoneinfoga", None, "medium", data)]
    except Exception:
        return []
