import re
import uuid
from datetime import datetime

EMAIL = re.compile(r'[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}')
PHONE = re.compile(r'\+?\d[\d .()\-]{8,}\d')
USER = re.compile(r'@([A-Za-z0-9_.]{3,30})')


def extract(result: dict) -> list[dict]:
    text = ' '.join(str(value) for value in (result.get('extracted_data') or {}).values())
    return ([{'lead_type': 'email', 'value': value} for value in set(EMAIL.findall(text))] + [{'lead_type': 'phone', 'value': value} for value in set(PHONE.findall(text))] + [{'lead_type': 'username', 'value': value} for value in set(USER.findall(text))])


def records(investigation_id: str, case_id: str, leads: list[dict]) -> list[dict]:
    return [{'id': str(uuid.uuid4()), 'investigation_id': investigation_id, 'source_case_id': case_id, 'lead_type': lead['lead_type'], 'value': lead['value'], 'auto_searched': False, 'created_at': datetime.utcnow().isoformat()} for lead in leads]
