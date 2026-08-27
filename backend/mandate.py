from typing import Tuple, Optional
from datetime import datetime, timezone
import db


def check_mandate(mandate_id: str, amount_paise: int, category: str, db_path: Optional[str] = None) -> Tuple[bool, str]:
    """
    Evaluates whether a purchase is authorized by checking mandate rules in order:
    1. Mandate exists
    2. Mandate is not revoked
    3. Expiry date has not passed
    4. Category matches
    5. Amount <= per-transaction cap
    6. Spent + Amount <= total cap
    """
    mandate = db.get_mandate(mandate_id, db_path=db_path) if db_path else db.get_mandate(mandate_id)

    if not mandate:
        return False, "mandate not found"

    if mandate.get("revoked") == 1:
        return False, "mandate revoked"

    expiry_dt = datetime.fromisoformat(mandate["expiry"])
    if datetime.now(timezone.utc) > expiry_dt:
        return False, "mandate expired"

    if mandate.get("category", "").lower() != category.lower():
        return False, "category not covered by mandate"

    if amount_paise > mandate.get("per_txn_cap_paise", 0):
        return False, "exceeds per-transaction cap"

    if mandate.get("spent_paise", 0) + amount_paise > mandate.get("total_cap_paise", 0):
        return False, "exceeds remaining total cap"

    return True, "approved"


def increment_spent(mandate_id: str, amount_paise: int, db_path: Optional[str] = None) -> None:
    # Only called AFTER Razorpay order creation succeeds to avoid burning budget on failures
    if db_path:
        db.update_mandate_spent(mandate_id, amount_paise, db_path=db_path)
    else:
        db.update_mandate_spent(mandate_id, amount_paise)
