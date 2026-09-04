import hmac
from fastapi import Header, HTTPException
from app.config import settings


def require_admin(x_admin_password: str = Header(default='')):
    if not x_admin_password or not hmac.compare_digest(x_admin_password, settings.admin_password):
        raise HTTPException(status_code=401, detail='Invalid or missing admin credentials.')
