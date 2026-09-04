from datetime import datetime
from typing import Any, Dict
import uuid


def result(case_id: str, tool: str, target: str, site: str | None = None, url: str | None = None, confidence: str = "medium", extracted_data: Dict[str, Any] | None = None) -> Dict[str, Any]:
    return {
        "id": str(uuid.uuid4()),
        "case_id": case_id,
        "tool": tool,
        "target": target,
        "site": site,
        "url": url,
        "confidence": confidence,
        "extracted_data": extracted_data or {},
        "created_at": datetime.utcnow().isoformat(),
    }
