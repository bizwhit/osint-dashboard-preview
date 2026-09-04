from datetime import datetime
import uuid
from app.db import supabase_client


def log_action(action: str, **kwargs) -> None:
    if not supabase_client:
        return
    row = {'id': str(uuid.uuid4()), 'action': action, 'created_at': datetime.utcnow().isoformat(), **kwargs}
    try:
        supabase_client.table('audit_logs').insert(row).execute()
    except Exception:
        pass
