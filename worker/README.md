Render Python web service

Root Directory: worker
Build Command: pip install -r requirements.txt && python download_data.py
Start Command: uvicorn worker:app --host 0.0.0.0 --port $PORT
Health Check Path: /health

Set PYTHON_VERSION=3.11.11 and WORKER_API_KEY to a long random secret in Render environment settings. Never commit that secret or embed it in browser code. Missing WORKER_API_KEY deliberately disables searches. Server-side callers must send Authorization: Bearer <WORKER_API_KEY>.

POST /search accepts username and limit (1-250). Returns raw Maigret JSON reports; frontend normalization and secure proxy integration are separate steps. No mock results. One concurrent search per process. No durable job queue; requests can time out. Recursion disabled for bounded initial testing. No CAPTCHA bypass. Respect site rules and search only public information for legitimate purposes.

After committing, deploy the latest main commit in Render. Verify /health before integrating the frontend. These files have not yet been runtime-tested on Render.
