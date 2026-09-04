from supabase import create_client
from app.config import settings

supabase_client = create_client(settings.supabase_url, settings.supabase_key) if settings.supabase_url and settings.supabase_key else None
