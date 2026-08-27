import os
import sys
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, Optional

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import db
import merchant
from seed import seed_database


def reset_mandate(mandate_id: str = "mandate_groceries_001", db_path: Optional[str] = None) -> None:
    conn = db.get_connection(db_path) if db_path else db.get_connection()
    cursor = conn.cursor()
    now = datetime.now(timezone.utc)
    future_expiry = (now + timedelta(days=7)).isoformat()
    cursor.execute(
        """
        UPDATE mandates
        SET spent_paise = 0, revoked = 0, expiry = ?
        WHERE id = ?
        """,
        (future_expiry, mandate_id),
    )
    conn.commit()
    conn.close()


def set_mandate_revoked(mandate_id: str = "mandate_groceries_001", revoked: int = 1, db_path: Optional[str] = None) -> None:
    conn = db.get_connection(db_path) if db_path else db.get_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE mandates SET revoked = ? WHERE id = ?", (revoked, mandate_id))
    conn.commit()
    conn.close()


def set_mandate_expiry(mandate_id: str = "mandate_groceries_001", expiry_iso: str = "2020-01-01T00:00:00+00:00", db_path: Optional[str] = None) -> None:
    conn = db.get_connection(db_path) if db_path else db.get_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE mandates SET expiry = ? WHERE id = ?", (expiry_iso, mandate_id))
    conn.commit()
    conn.close()


def set_mandate_spent(mandate_id: str = "mandate_groceries_001", spent_paise: int = 0, db_path: Optional[str] = None) -> None:
    conn = db.get_connection(db_path) if db_path else db.get_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE mandates SET spent_paise = ? WHERE id = ?", (spent_paise, mandate_id))
    conn.commit()
    conn.close()


def run_all_scenarios(mandate_id: str = "mandate_groceries_001", db_path: Optional[str] = None) -> None:
    mandate_row = db.get_mandate(mandate_id, db_path=db_path) if db_path else db.get_mandate(mandate_id)
    if not mandate_row:
        seed_database(db_path=db_path) if db_path else seed_database()

    # Reset mandate to clean baseline before running test scenarios
    reset_mandate(mandate_id=mandate_id, db_path=db_path)

    initial_logs = db.get_audit_logs(db_path=db_path) if db_path else db.get_audit_logs()
    initial_log_count = len(initial_logs)

    print("=" * 80)
    print("             BOUNDED AGENTIC CHECKOUT - DEMO SCENARIOS")
    print("=" * 80)
    print(f"Mandate ID: {mandate_id} | Per-Txn Cap: INR 500.00 | Total Cap: INR 2000.00")
    print("-" * 80)

    # Scenario 1: Normal purchase within both per-txn and total caps
    items_1 = ["item_groc_01", "item_groc_02"]
    res_1 = merchant.attempt_checkout(mandate_id, items_1, db_path=db_path)
    status_1 = "APPROVED" if res_1["approved"] else "BLOCKED"
    amount_inr_1 = res_1["amount_paise"] / 100.0
    print(f"[Scenario 1] Normal Purchase: {status_1} | Amount: INR {amount_inr_1:.2f} | Reason: {res_1['reason']} | Razorpay Order: {res_1['razorpay_order_id']}")

    # Scenario 2: Second purchase bringing cumulative spend close to total cap
    set_mandate_spent(mandate_id, spent_paise=155000, db_path=db_path)
    items_2 = ["item_groc_01", "item_groc_02"]
    res_2 = merchant.attempt_checkout(mandate_id, items_2, db_path=db_path)
    status_2 = "APPROVED" if res_2["approved"] else "BLOCKED"
    amount_inr_2 = res_2["amount_paise"] / 100.0
    updated_mandate = db.get_mandate(mandate_id, db_path=db_path) if db_path else db.get_mandate(mandate_id)
    cumulative_spend_inr = updated_mandate["spent_paise"] / 100.0
    print(f"[Scenario 2] High Cumulative Spend: {status_2} | Amount: INR {amount_inr_2:.2f} | Reason: {res_2['reason']} | Razorpay Order: {res_2['razorpay_order_id']} (Total Spend: INR {cumulative_spend_inr:.2f} / 2000.00)")

    # Scenario 3: Exceeds per-transaction cap (INR 580 > INR 500 cap)
    items_3 = ["item_groc_01", "item_groc_02", "item_groc_05"]
    res_3 = merchant.attempt_checkout(mandate_id, items_3, db_path=db_path)
    status_3 = "APPROVED" if res_3["approved"] else "BLOCKED"
    amount_inr_3 = res_3["amount_paise"] / 100.0
    print(f"[Scenario 3] Exceeds Per-Txn Cap: {status_3} | Amount: INR {amount_inr_3:.2f} | Reason: {res_3['reason']} | Razorpay Order: {res_3['razorpay_order_id']}")

    # Scenario 4: Purchase attempt on a revoked mandate
    set_mandate_revoked(mandate_id, revoked=1, db_path=db_path)
    items_4 = ["item_groc_03", "item_groc_04"]
    res_4 = merchant.attempt_checkout(mandate_id, items_4, db_path=db_path)
    status_4 = "APPROVED" if res_4["approved"] else "BLOCKED"
    amount_inr_4 = res_4["amount_paise"] / 100.0
    print(f"[Scenario 4] Revoked Mandate: {status_4} | Amount: INR {amount_inr_4:.2f} | Reason: {res_4['reason']} | Razorpay Order: {res_4['razorpay_order_id']}")

    # Scenario 5: Purchase attempt on an expired mandate
    set_mandate_revoked(mandate_id, revoked=0, db_path=db_path)
    set_mandate_expiry(mandate_id, expiry_iso="2020-01-01T00:00:00+00:00", db_path=db_path)
    items_5 = ["item_groc_03", "item_groc_04"]
    res_5 = merchant.attempt_checkout(mandate_id, items_5, db_path=db_path)
    status_5 = "APPROVED" if res_5["approved"] else "BLOCKED"
    amount_inr_5 = res_5["amount_paise"] / 100.0
    print(f"[Scenario 5] Expired Mandate: {status_5} | Amount: INR {amount_inr_5:.2f} | Reason: {res_5['reason']} | Razorpay Order: {res_5['razorpay_order_id']}")

    # Check that every single attempt was logged to the database
    final_logs = db.get_audit_logs(db_path=db_path) if db_path else db.get_audit_logs()
    total_logs = len(final_logs)
    new_logs = total_logs - initial_log_count

    print("-" * 80)
    print(f"Audit Trail: {new_logs} attempts logged in SQLite (Total records: {total_logs}).")
    print("=" * 80)


if __name__ == "__main__":
    run_all_scenarios()
