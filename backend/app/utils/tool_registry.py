from dataclasses import dataclass
from typing import Dict, List
import asyncio
import shutil
import subprocess
import httpx
from app.config import settings


@dataclass(frozen=True)
class Tool:
    id: str
    name: str
    category: str
    input_types: List[str]
    description: str
    default_enabled: bool = True


TOOLS: Dict[str, Tool] = {
    'sherlock': Tool('sherlock', 'Sherlock', 'Username', ['username'], 'Public username discovery across supported sites.'),
    'maigret': Tool('maigret', 'Maigret', 'Username', ['username'], 'Username research with public profile extraction.'),
    'whatsmyname': Tool('whatsmyname', 'WhatsMyName', 'Username', ['username'], 'Dataset-driven username checks across community-maintained sites.'),
    'holehe': Tool('holehe', 'Holehe', 'Email', ['email'], 'Email-to-service association checks.'),
    'theharvester': Tool('theharvester', 'theHarvester', 'Email / Domain', ['email', 'domain'], 'Public email, host, and subdomain collection.'),
    'phoneinfoga': Tool('phoneinfoga', 'PhoneInfoga', 'Phone', ['phone'], 'Phone metadata and public footprint collection.'),
    'spiderfoot': Tool('spiderfoot', 'SpiderFoot', 'Domain', ['domain'], 'Managed domain footprint scan service.'),
}


def tools_for_input_type(input_type: str) -> List[Tool]:
    return [tool for tool in TOOLS.values() if input_type in tool.input_types]


def validate_selected_tools(input_type: str, selected_tools: List[str] | None) -> List[str]:
    valid = {tool.id for tool in tools_for_input_type(input_type)}
    selected = selected_tools if selected_tools is not None else [tool.id for tool in tools_for_input_type(input_type) if tool.default_enabled]
    invalid = set(selected) - valid
    if invalid:
        raise ValueError(f'Unsupported tool(s) for {input_type}: {", ".join(sorted(invalid))}')
    return list(dict.fromkeys(selected))


def _cli_health(command: str) -> dict:
    if not shutil.which(command):
        return {'status': 'unavailable', 'detail': f'{command} is not on PATH'}
    try:
        out = subprocess.run([command, '--version'], capture_output=True, text=True, timeout=10)
        detail = (out.stdout or out.stderr or 'installed').strip().splitlines()[0]
        return {'status': 'healthy' if out.returncode == 0 else 'degraded', 'detail': detail[:200]}
    except Exception as exc:
        return {'status': 'degraded', 'detail': str(exc)[:200]}


async def health_for_tool(tool_id: str) -> dict:
    tool = TOOLS[tool_id]
    if tool_id == 'spiderfoot':
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                response = await client.get(settings.spiderfoot_url)
            health = {'status': 'healthy' if response.status_code < 500 else 'degraded', 'detail': f'HTTP {response.status_code}'}
        except Exception as exc:
            health = {'status': 'unavailable', 'detail': str(exc)[:200]}
    elif tool_id == 'whatsmyname':
        from app.utils.whatsmyname_client import load_sites
        count = len(load_sites())
        health = {'status': 'healthy' if count else 'unavailable', 'detail': f'{count} dataset sites loaded'}
    else:
        health = _cli_health(tool_id)
    return {'id': tool.id, 'name': tool.name, 'category': tool.category, 'input_types': tool.input_types, 'description': tool.description, 'default_enabled': tool.default_enabled, **health}


async def all_tool_health() -> List[dict]:
    return await asyncio.gather(*(health_for_tool(tool_id) for tool_id in TOOLS))
