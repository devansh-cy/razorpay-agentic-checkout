import os
import sqlite3
from typing import List, Dict, Any, Optional

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "app.db")


def get_connection(db_path: str = DB_PATH) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def init_db(db_path: str = DB_PATH) -> None:
    conn = get_connection(db_path)
    cursor = conn.cursor()

    cursor.executescript("""
    CREATE TABLE IF NOT EXISTS mandates (
        id TEXT PRIMARY KEY,
        agent_id TEXT NOT NULL,
        merchant_id TEXT NOT NULL,
        category TEXT NOT NULL,
        per_txn_cap_paise INTEGER NOT NULL,
        total_cap_paise INTEGER NOT NULL,
        spent_paise INTEGER DEFAULT 0,
        expiry TEXT NOT NULL,
        revoked INTEGER DEFAULT 0,
        created_at TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS catalog (
        id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        category TEXT NOT NULL,
        price_paise INTEGER NOT NULL,
        stock INTEGER NOT NULL
    );

    CREATE TABLE IF NOT EXISTS orders (
        id TEXT PRIMARY KEY,
        mandate_id TEXT NOT NULL,
        razorpay_order_id TEXT NOT NULL,
        amount_paise INTEGER NOT NULL,
        status TEXT NOT NULL,
        created_at TEXT NOT NULL,
        FOREIGN KEY (mandate_id) REFERENCES mandates (id)
    );

    CREATE TABLE IF NOT EXISTS audit_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp TEXT NOT NULL,
        mandate_id TEXT NOT NULL,
        agent_id TEXT NOT NULL,
        attempted_amount_paise INTEGER NOT NULL,
        items_json TEXT NOT NULL,
        approved INTEGER NOT NULL,
        reason TEXT NOT NULL,
        razorpay_order_id TEXT
    );
    """)

    conn.commit()
    conn.close()


def insert_mandate(mandate_data: Dict[str, Any], db_path: str = DB_PATH) -> None:
    conn = get_connection(db_path)
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO mandates (id, agent_id, merchant_id, category, per_txn_cap_paise, total_cap_paise, spent_paise, expiry, revoked, created_at)
        VALUES (:id, :agent_id, :merchant_id, :category, :per_txn_cap_paise, :total_cap_paise, :spent_paise, :expiry, :revoked, :created_at)
        """,
        {
            "id": mandate_data["id"],
            "agent_id": mandate_data["agent_id"],
            "merchant_id": mandate_data["merchant_id"],
            "category": mandate_data["category"],
            "per_txn_cap_paise": mandate_data["per_txn_cap_paise"],
            "total_cap_paise": mandate_data["total_cap_paise"],
            "spent_paise": mandate_data.get("spent_paise", 0),
            "expiry": mandate_data["expiry"],
            "revoked": mandate_data.get("revoked", 0),
            "created_at": mandate_data["created_at"],
        },
    )
    conn.commit()
    conn.close()


def get_mandate(mandate_id: str, db_path: str = DB_PATH) -> Optional[Dict[str, Any]]:
    conn = get_connection(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM mandates WHERE id = ?", (mandate_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None


def get_all_mandates(db_path: str = DB_PATH) -> List[Dict[str, Any]]:
    conn = get_connection(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM mandates ORDER BY created_at DESC")
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


def update_mandate_spent(mandate_id: str, additional_spent_paise: int, db_path: str = DB_PATH) -> None:
    conn = get_connection(db_path)
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE mandates SET spent_paise = spent_paise + ? WHERE id = ?",
        (additional_spent_paise, mandate_id),
    )
    conn.commit()
    conn.close()


def insert_catalog_item(item_data: Dict[str, Any], db_path: str = DB_PATH) -> None:
    conn = get_connection(db_path)
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO catalog (id, name, category, price_paise, stock)
        VALUES (:id, :name, :category, :price_paise, :stock)
        """,
        {
            "id": item_data["id"],
            "name": item_data["name"],
            "category": item_data["category"],
            "price_paise": item_data["price_paise"],
            "stock": item_data["stock"],
        },
    )
    conn.commit()
    conn.close()


def get_catalog(category: Optional[str] = None, db_path: str = DB_PATH) -> List[Dict[str, Any]]:
    conn = get_connection(db_path)
    cursor = conn.cursor()
    if category:
        cursor.execute("SELECT * FROM catalog WHERE category = ? ORDER BY name ASC", (category,))
    else:
        cursor.execute("SELECT * FROM catalog ORDER BY category ASC, name ASC")
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


def get_catalog_item(item_id: str, db_path: str = DB_PATH) -> Optional[Dict[str, Any]]:
    conn = get_connection(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM catalog WHERE id = ?", (item_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None


def insert_order(order_data: Dict[str, Any], db_path: str = DB_PATH) -> None:
    conn = get_connection(db_path)
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO orders (id, mandate_id, razorpay_order_id, amount_paise, status, created_at)
        VALUES (:id, :mandate_id, :razorpay_order_id, :amount_paise, :status, :created_at)
        """,
        {
            "id": order_data["id"],
            "mandate_id": order_data["mandate_id"],
            "razorpay_order_id": order_data["razorpay_order_id"],
            "amount_paise": order_data["amount_paise"],
            "status": order_data["status"],
            "created_at": order_data["created_at"],
        },
    )
    conn.commit()
    conn.close()


def get_orders(mandate_id: Optional[str] = None, db_path: str = DB_PATH) -> List[Dict[str, Any]]:
    conn = get_connection(db_path)
    cursor = conn.cursor()
    if mandate_id:
        cursor.execute("SELECT * FROM orders WHERE mandate_id = ? ORDER BY created_at DESC", (mandate_id,))
    else:
        cursor.execute("SELECT * FROM orders ORDER BY created_at DESC")
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


def insert_audit_log(log_data: Dict[str, Any], db_path: str = DB_PATH) -> int:
    conn = get_connection(db_path)
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO audit_log (timestamp, mandate_id, agent_id, attempted_amount_paise, items_json, approved, reason, razorpay_order_id)
        VALUES (:timestamp, :mandate_id, :agent_id, :attempted_amount_paise, :items_json, :approved, :reason, :razorpay_order_id)
        """,
        {
            "timestamp": log_data["timestamp"],
            "mandate_id": log_data["mandate_id"],
            "agent_id": log_data["agent_id"],
            "attempted_amount_paise": log_data["attempted_amount_paise"],
            "items_json": log_data["items_json"],
            "approved": log_data["approved"],
            "reason": log_data["reason"],
            "razorpay_order_id": log_data.get("razorpay_order_id"),
        },
    )
    conn.commit()
    inserted_id = cursor.lastrowid
    conn.close()
    return inserted_id


def get_audit_logs(mandate_id: Optional[str] = None, db_path: str = DB_PATH) -> List[Dict[str, Any]]:
    conn = get_connection(db_path)
    cursor = conn.cursor()
    if mandate_id:
        cursor.execute("SELECT * FROM audit_log WHERE mandate_id = ? ORDER BY id DESC", (mandate_id,))
    else:
        cursor.execute("SELECT * FROM audit_log ORDER BY id DESC")
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]
