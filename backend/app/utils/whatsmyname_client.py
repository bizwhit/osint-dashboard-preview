import asyncio
import json
from pathlib import Path
from typing import Any, Dict, List
import httpx

DATA_PATH = Path("/app/data/wmn-data.json")
MAX_CONCURRENCY = 20


def load_sites() -> List[Dict[str, Any]]:
    if not DATA_PATH.exists():
        return []
    data = json.loads(DATA_PATH.read_text(encoding="utf-8"))
    return data.get("sites", data if isinstance(data, list) else [])


async def _check(client: httpx.AsyncClient, item: Dict[str, Any], username: str, sem: asyncio.Semaphore):
    pattern = item.get("uri_check", "")
    if "{account}" not in pattern:
        return None
    url = pattern.replace("{account}", username)
    async with sem:
        try:
            response = await client.get(url, follow_redirects=True, timeout=8)
        except httpx.RequestError:
            return None
    code_ok = item.get("e_code") is None or response.status_code == item.get("e_code")
    marker = item.get("e_string", "")
    marker_ok = not marker or marker in response.text
    if not (code_ok and marker_ok):
        return None
    return {
        "site": item.get("name", "unknown"),
        "url": item.get("uri_pretty", pattern).replace("{account}", username),
        "category": item.get("cat", "unknown"),
    }


async def search(username: str, tags: List[str] | None = None) -> List[Dict[str, Any]]:
    sites = load_sites()
    if tags:
        wanted = {tag.lower() for tag in tags}
        sites = [site for site in sites if site.get("cat", "").lower() in wanted]
    sem = asyncio.Semaphore(MAX_CONCURRENCY)
    async with httpx.AsyncClient() as client:
        found = await asyncio.gather(*[_check(client, site, username, sem) for site in sites])
    return [item for item in found if item]
