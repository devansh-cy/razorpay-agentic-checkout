import os
from datetime import datetime, timedelta, timezone
from db import init_db, insert_mandate, insert_catalog_item, DB_PATH


def seed_database(db_path: str = DB_PATH) -> None:
    if os.path.exists(db_path):
        os.remove(db_path)

    init_db(db_path)

    now = datetime.now(timezone.utc)
    expiry = now + timedelta(days=7)

    mandate_data = {
        "id": "mandate_groceries_001",
        "agent_id": "buyer_agent_alpha",
        "merchant_id": "merchant_quickmart",
        "category": "groceries",
        "per_txn_cap_paise": 50000,
        "total_cap_paise": 200000,
        "spent_paise": 0,
        "expiry": expiry.isoformat(),
        "revoked": 0,
        "created_at": now.isoformat(),
    }
    insert_mandate(mandate_data, db_path=db_path)

    catalog_items = [
        {
            "id": "item_groc_01",
            "name": "Aashirvaad Whole Wheat Atta 5kg",
            "category": "groceries",
            "price_paise": 27500,
            "stock": 50,
        },
        {
            "id": "item_groc_02",
            "name": "Fortune Sunlite Sunflower Oil 1L",
            "category": "groceries",
            "price_paise": 14500,
            "stock": 40,
        },
        {
            "id": "item_groc_03",
            "name": "Amul Taaza Toned Milk 1L",
            "category": "groceries",
            "price_paise": 5600,
            "stock": 100,
        },
        {
            "id": "item_groc_04",
            "name": "Tata Salt Iodized 1kg",
            "category": "groceries",
            "price_paise": 2800,
            "stock": 150,
        },
        {
            "id": "item_groc_05",
            "name": "India Gate Basmati Rice 1kg",
            "category": "groceries",
            "price_paise": 16000,
            "stock": 60,
        },
        {
            "id": "item_groc_06",
            "name": "Organic Turmeric Powder 200g",
            "category": "groceries",
            "price_paise": 6500,
            "stock": 80,
        },
        {
            "id": "item_groc_07",
            "name": "Maggi 2-Minute Noodles 4-Pack",
            "category": "groceries",
            "price_paise": 5800,
            "stock": 120,
        },
        {
            "id": "item_groc_08",
            "name": "Nescafe Classic Coffee 50g",
            "category": "groceries",
            "price_paise": 18500,
            "stock": 45,
        },
    ]

    for item in catalog_items:
        insert_catalog_item(item, db_path=db_path)

    print("==================================================")
    print(" Database Seeded Successfully!")
    print("==================================================")
    print(f"Mandate ID           : {mandate_data['id']}")
    print(f"Category             : {mandate_data['category']}")
    print(f"Per-Txn Cap          : INR {mandate_data['per_txn_cap_paise'] / 100:.2f} ({mandate_data['per_txn_cap_paise']} paise)")
    print(f"Total Cap            : INR {mandate_data['total_cap_paise'] / 100:.2f} ({mandate_data['total_cap_paise']} paise)")
    print(f"Spent                : INR {mandate_data['spent_paise'] / 100:.2f} ({mandate_data['spent_paise']} paise)")
    print(f"Expiry               : {mandate_data['expiry']}")
    print(f"Catalog Items Seeded : {len(catalog_items)}")
    print("==================================================")


if __name__ == "__main__":
    seed_database()
