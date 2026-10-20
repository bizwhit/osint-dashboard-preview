import asyncio
import hmac
import json
import os
import shutil
import tempfile
from pathlib import Path
from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel, Field

app = FastAPI(title='Maigret worker')
lock = asyncio.Lock()

class Search(BaseModel):
    username: str = Field(min_length=1, max_length=64, pattern=r'^[A-Za-z0-9_][A-Za-z0-9_.-]*$')
    limit: int = Field(default=100, ge=1, le=250)

@app.get('/health')
async def health():
    return {'status': 'ok', 'engine_available': bool(shutil.which('maigret')), 'search_configured': bool(os.getenv('WORKER_API_KEY'))}

@app.post('/search')
async def search(body: Search, authorization: str = Header(default='')):
    key = os.getenv('WORKER_API_KEY', '')
    if not key:
        raise HTTPException(503, 'Set WORKER_API_KEY in Render environment settings')
    if not hmac.compare_digest(authorization, 'Bearer ' + key):
        raise HTTPException(401, 'Unauthorized')
    if lock.locked():
        raise HTTPException(429, 'Worker busy; retry later')
    async with lock:
        with tempfile.TemporaryDirectory() as folder:
            process = await asyncio.create_subprocess_exec('maigret', body.username, '--top-sites', str(body.limit), '--timeout', '10', '--no-recursion', '--json', 'simple', '--folderoutput', folder, stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.DEVNULL)
            try:
                await asyncio.wait_for(process.wait(), timeout=180)
            except (asyncio.TimeoutError, asyncio.CancelledError):
                if process.returncode is None:
                    process.kill()
                await process.wait()
                raise HTTPException(504, 'Search timed out or was cancelled')
            reports = list(Path(folder).rglob('*.json'))
            if process.returncode != 0 or not reports:
                raise HTTPException(502, 'Maigret failed to produce a report; inspect worker deployment and engine version')
            try:
                data = [json.loads(p.read_text(encoding='utf-8')) for p in reports]
            except (ValueError, OSError):
                raise HTTPException(502, 'Invalid engine report')
            return {'username': body.username, 'requested_site_limit': body.limit, 'engine': 'maigret', 'reports': data, 'notice': 'Raw engine reports. Username matches are candidates, not proof of identity.'}
