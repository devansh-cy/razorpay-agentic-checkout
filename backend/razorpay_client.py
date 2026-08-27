import os
import uuid
from typing import Dict, Any, Optional
from dotenv import load_dotenv

load_dotenv()


def get_razorpay_client():
    import razorpay

    key_id = os.getenv("RAZORPAY_KEY_ID")
    key_secret = os.getenv("RAZORPAY_KEY_SECRET")

    if not key_id or not key_secret or key_id == "your_razorpay_key_id":
        raise ValueError("Valid RAZORPAY_KEY_ID and RAZORPAY_KEY_SECRET must be set in .env")

    return razorpay.Client(auth=(key_id, key_secret))


def create_order(amount_paise: int, mandate_id: str, agent_id: str, reason: str) -> Dict[str, Any]:
    try:
        client = get_razorpay_client()
        receipt_id = f"rcpt_{uuid.uuid4().hex[:12]}"

        notes = {
            "mandate_id": str(mandate_id)[:250],
            "agent_id": str(agent_id)[:250],
            "reason": str(reason)[:250],
        }

        data = {
            "amount": amount_paise,
            "currency": "INR",
            "receipt": receipt_id,
            "notes": notes,
        }

        order = client.order.create(data=data)
        return {
            "id": order.get("id"),
            "status": order.get("status"),
            "order": order,
        }
    except Exception as e:
        return {
            "id": None,
            "status": "error",
            "error": str(e),
        }


def create_razorpay_order(amount_paise: int, receipt_id: str, currency: str = "INR", notes: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
    client = get_razorpay_client()
    data = {
        "amount": amount_paise,
        "currency": currency,
        "receipt": receipt_id,
        "notes": notes or {},
    }
    return client.order.create(data=data)
