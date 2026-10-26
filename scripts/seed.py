"""Load the fake customers and interactions into Supabase.

Run from the project root:  python -m scripts.seed
Safe to run twice: customers are upserted, interactions are only added once.
"""
import json
from pathlib import Path

from app.core.db import supabase

DATA = Path("data/synthetic")


def main() -> None:
    customers = json.loads((DATA / "customers.json").read_text(encoding="utf-8"))
    result = supabase.table("customers").upsert(customers, on_conflict="name").execute()
    id_by_name = {row["name"]: row["id"] for row in result.data}
    print(f"Customers in database: {len(id_by_name)}")

    existing = supabase.table("interactions").select("id").limit(1).execute()
    if existing.data:
        print("Interactions already seeded - skipping.")
        return

    items = json.loads((DATA / "interactions.json").read_text(encoding="utf-8"))
    rows = [
        {
            "customer_id": id_by_name[item["customer"]],
            "channel": item["channel"],
            "content": item["content"],
            "occurred_at": item["occurred_at"],
        }
        for item in items
    ]
    supabase.table("interactions").insert(rows).execute()
    print(f"Interactions inserted: {len(rows)}")


if __name__ == "__main__":
    main()
