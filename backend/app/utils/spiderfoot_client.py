import asyncio
from typing import Any, Dict, List
import httpx
from app.config import settings


async def run_domain_scan(target: str, timeout_seconds: int = 480) -> List[Dict[str, Any]]:
    """Start a SpiderFoot scan, wait for completion, and return normalized events."""
    async with httpx.AsyncClient(timeout=30) as client:
        start = await client.post(f"{settings.spiderfoot_url}/startscan", data={"scanname": f"osint-{target}", "scantarget": target, "modulelist": "sfp_dnsresolve,sfp_whois,sfp_email,sfp_subdomain_enum"})
        start.raise_for_status()
        scan_id = start.text.strip().strip('"')
        elapsed = 0
        while elapsed < timeout_seconds:
            status = await client.get(f"{settings.spiderfoot_url}/scanstatus", params={"id": scan_id})
            status.raise_for_status()
            data = status.json()
            state = data[5] if isinstance(data, list) and len(data) > 5 else "UNKNOWN"
            if state == "FINISHED":
                break
            if state in {"ABORTED", "ERROR-FAILED"}:
                return []
            await asyncio.sleep(5)
            elapsed += 5
        events = await client.get(f"{settings.spiderfoot_url}/scaneventresults", params={"id": scan_id, "eventType": "ALL"})
        events.raise_for_status()
    return [{"type": row[4] if len(row) > 4 else "unknown", "data": row[1] if len(row) > 1 else "", "module": row[3] if len(row) > 3 else "spiderfoot"} for row in events.json() or []]
