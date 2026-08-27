import json
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
import db


def log_attempt(
    mandate_id: str,
    agent_id: str,
    attempted_amount_paise: int,
    items: List[Dict[str, Any]],
    approved: bool,
    reason: str,
    razorpay_order_id: Optional[str] = None,
    db_path: Optional[str] = None,
) -> int:
    log_entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "mandate_id": mandate_id,
        "agent_id": agent_id,
        "attempted_amount_paise": attempted_amount_paise,
        "items_json": json.dumps(items),
        "approved": 1 if approved else 0,
        "reason": reason,
        "razorpay_order_id": razorpay_order_id,
    }
    
    if db_path:
        return db.insert_audit_log(log_entry, db_path=db_path)
    return db.insert_audit_log(log_entry)
