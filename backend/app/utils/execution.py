"""Shared persistence and lifecycle helpers for Celery OSINT workers."""
from datetime import datetime
from typing import Any, Dict, Iterable, List
from app.db import supabase_client
from app.utils.lead_detector import extract, records
from app.utils.progress import publish


def now() -> str:
    return datetime.utcnow().isoformat()


def update_case(case_id: str, status: str) -> None:
    if not supabase_client:
        return
    data: Dict[str, Any] = {"status": status}
    if status == "running":
        data["started_at"] = now()
    if status in {"completed", "failed"}:
        data["completed_at"] = now()
    supabase_client.table("cases").update(data).eq("id", case_id).execute()


def save_results(rows: List[Dict[str, Any]]) -> None:
    if supabase_client and rows:
        supabase_client.table("search_results").insert(rows).execute()


def save_leads(investigation_id: str | None, case_id: str, results: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
    if not investigation_id or not supabase_client:
        return []
    seen: set[tuple[str, str]] = set()
    discovered: List[Dict[str, Any]] = []
    for item in results:
        for lead in extract(item):
            key = (lead["lead_type"], lead["value"].lower())
            if key not in seen and lead["value"].lower() != str(item.get("target", "")).lower():
                seen.add(key)
                discovered.append(lead)
    rows = records(investigation_id, case_id, discovered)
    if rows:
        supabase_client.table("leads").insert(rows).execute()
        publish(case_id, "lead_detector", "completed", len(rows))
    return rows


def mark_case_running(case_id: str) -> None:
    update_case(case_id, "running")
    publish(case_id, "case", "running")


def mark_case_complete(case_id: str, results_count: int) -> None:
    update_case(case_id, "completed")
    publish(case_id, "case", "completed", results_count)


def mark_case_failed(case_id: str, detail: str = "") -> None:
    update_case(case_id, "failed")
    publish(case_id, "case", "failed")
