"""Deployment entrypoint with an explicit CORS allowlist."""
import os
from fastapi.middleware.cors import CORSMiddleware
from app.main import app

origins = [value.strip() for value in os.environ.get('CORS_ORIGINS', '').split(',') if value.strip()]
if not origins or '*' in origins:
    raise RuntimeError('CORS_ORIGINS must be an explicit, non-wildcard allowlist')
password = os.environ.get('ADMIN_PASSWORD', '')
if len(password) < 24 or password == 'change-me-before-deploying':
    raise RuntimeError('ADMIN_PASSWORD must be unique and at least 24 characters')
app.user_middleware = [entry for entry in app.user_middleware if entry.cls is not CORSMiddleware]
app.add_middleware(CORSMiddleware, allow_origins=origins, allow_credentials=True,
                   allow_methods=['GET', 'POST'], allow_headers=['Content-Type', 'X-Admin-Password'],
                   expose_headers=['Retry-After'])
