from typing import List, Dict, Any, Optional
import db
import mandate
import razorpay_client
import audit


def get_catalog(category: Optional[str] = None, db_path: Optional[str] = None) -> List[Dict[str, Any]]:
    # Fetches catalog items from the database, optionally filtered by category
    if db_path:
        return db.get_catalog(category=category, db_path=db_path)
    return db.get_catalog(category=category)


def attempt_checkout(mandate_id: str, item_ids: List[str], db_path: Optional[str] = None) -> Dict[str, Any]:
    # Look up item details and calculate total amount
    items = []
    total_amount_paise = 0
    categories = []

    for item_id in item_ids:
        if db_path:
            catalog_item = db.get_catalog_item(item_id, db_path=db_path)
        else:
            catalog_item = db.get_catalog_item(item_id)

        if catalog_item:
            items.append(catalog_item)
            total_amount_paise += catalog_item.get("price_paise", 0)
            if catalog_item.get("category"):
                categories.append(catalog_item.get("category"))
        else:
            items.append({"id": item_id, "name": f"Unknown ({item_id})", "price_paise": 0})

    category = categories[0] if categories else "groceries"

    mandate_row = db.get_mandate(mandate_id, db_path=db_path) if db_path else db.get_mandate(mandate_id)
    agent_id = mandate_row.get("agent_id", "buyer_agent_alpha") if mandate_row else "buyer_agent_alpha"

    # Step 1: Check mandate rules before making any external API call
    approved, reason = mandate.check_mandate(mandate_id, total_amount_paise, category, db_path=db_path)
    razorpay_order_id = None

    # Step 2: If approved, place order via Razorpay test-mode API
    if approved:
        order_res = razorpay_client.create_order(
            amount_paise=total_amount_paise,
            mandate_id=mandate_id,
            agent_id=agent_id,
            reason=reason
        )
        
        if order_res.get("id") and order_res.get("status") != "error":
            razorpay_order_id = order_res.get("id")
            # Step 3: Increment mandate spent only after Razorpay confirms order creation
            mandate.increment_spent(mandate_id, total_amount_paise, db_path=db_path)
        else:
            approved = False
            reason = f"Razorpay order creation failed: {order_res.get('error')}"
            razorpay_order_id = None

    # Step 4: Always log the attempt (approved or blocked) to audit trail
    audit.log_attempt(
        mandate_id=mandate_id,
        agent_id=agent_id,
        attempted_amount_paise=total_amount_paise,
        items=items,
        approved=approved,
        reason=reason,
        razorpay_order_id=razorpay_order_id,
        db_path=db_path
    )

    return {
        "approved": approved,
        "reason": reason,
        "razorpay_order_id": razorpay_order_id,
        "amount_paise": total_amount_paise,
        "items": items,
    }
